import optparse
import os
import kubernetes
import enum
import time
import json
import glob
import analyze
import controllers
import oracle
import yaml
import subprocess
import signal


def watch_crd(project, addrs):
    for addr in addrs:
        for crd in controllers.CRDs[project]:
            os.system("kubectl get %s -s %s" % (crd, addr))


def generate_configmap(test_config):
    yaml_map = yaml.safe_load(open(test_config))
    configmap = {}
    configmap["apiVersion"] = "v1"
    configmap["kind"] = "ConfigMap"
    configmap["metadata"] = {"name": "sonar-testing-global-config"}
    configmap["data"] = {}
    for key in yaml_map:
        if isinstance(yaml_map[key], list):
            assert key.endswith("-list")
            configmap["data"]["SONAR-" + key.upper()] = ",".join(yaml_map[key])
        else:
            configmap["data"]["SONAR-" + key.upper()] = yaml_map[key]
    configmap_path = "%s-configmap.yaml" % test_config[:-5]
    yaml.dump(configmap, open(configmap_path, "w"), sort_keys=False)
    return configmap_path


def kind_config(num_apiservers, num_workers):
    kind_config_filename = "kind-%sa-%sw.yaml" % (
        str(num_apiservers), str(num_workers))
    kind_config_file = open(kind_config_filename, "w")
    kind_config_file.writelines(
        ["kind: Cluster\n", "apiVersion: kind.x-k8s.io/v1alpha4\n", "nodes:\n"])
    for i in range(num_apiservers):
        kind_config_file.write("- role: control-plane\n")
    for i in range(num_workers):
        kind_config_file.write("- role: worker\n")
    kind_config_file.close()
    return kind_config_filename


def redirect_workers(num_workers):
    target_master = controllers.front_runner
    for i in range(num_workers):
        worker = "kind-worker" + (str(i+1) if i > 0 else "")
        os.system("docker exec %s bash -c \"sed -i 's/kind-external-load-balancer/%s/g' /etc/kubernetes/kubelet.conf\"" %
                  (worker, target_master))
        os.system("docker exec %s bash -c \"systemctl restart kubelet\"" % worker)


def setup_cluster(project, stage, mode, test_config, docker_repo, docker_tag, num_apiservers, num_workers):
    os.system("cp %s sonar-server/server.yaml" % test_config)
    os.system("kind delete cluster")

    os.system("./setup.sh %s %s %s" %
              (kind_config(num_apiservers, num_workers), docker_repo, docker_tag))

    # when testing time-travel, we need to pause the apiserver
    # if workers talks to the paused apiserver, the whole cluster will be slowed down
    # so we need to redirect the workers to other apiservers
    if mode == "time-travel" and stage == "test":
        redirect_workers(num_workers)

    os.system("./bypass-balancer.sh")

    configmap = generate_configmap(test_config)
    os.system("kubectl apply -f %s" % configmap)

    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()

    # Then we wait apiservers to be ready
    apiserver_list = []
    for i in range(num_apiservers):
        apiserver_name = "kube-apiserver-kind-control-plane" + \
            ("" if i == 0 else str(i + 1))
        apiserver_list.append(apiserver_name)

    for tick in range(600):
        created = core_v1.list_namespaced_pod(
            "kube-system", watch=False, label_selector="component=kube-apiserver").items
        if len(created) == len(apiserver_list) and len(created) == len([item for item in created if item.status.phase == "Running"]):
            break
        time.sleep(1)

    for apiserver in apiserver_list:
        os.system("kubectl cp %s %s:/sonar.yaml -n kube-system" %
                  (test_config, apiserver))

    # Preload operator image to kind nodes
    image = "%s/%s:%s" % (docker_repo, project, docker_tag)
    kind_load_cmd = "kind load docker-image %s" % (image)
    print("we are loading image %s to kind nodes..." % (image))
    if os.WEXITSTATUS(os.system(kind_load_cmd)):
        print("cannot load image %s locally, try to pull from remote" % (image))
        os.system("docker pull %s" % (image))
        os.system(kind_load_cmd)

    controllers.deploy[project](docker_repo, docker_tag)

    # Wait for project pod ready
    for tick in range(600):
        project_pod = core_v1.list_namespaced_pod(
            "default", watch=False, label_selector="sonartag="+project).items
        if len(project_pod) >= 1:
            if project_pod[0].status.phase == "Running":
                break
        time.sleep(1)

    apiserver_addr_list = []
    for i in range(num_apiservers):
        label_selector = "kubernetes.io/hostname=kind-control-plane" + \
            ("" if i == 0 else str(i + 1))
        apiserver_addr = "https://" + core_v1.list_node(
            watch=False, label_selector=label_selector).items[0].status.addresses[0].address + ":6443"
        apiserver_addr_list.append(apiserver_addr)
    watch_crd(project, apiserver_addr_list)


def run_workload(project, mode, test_workload, log_dir, num_apiservers):
    kubernetes.config.load_kube_config()
    pod_name = kubernetes.client.CoreV1Api().list_namespaced_pod(
        "default", watch=False, label_selector="sonartag="+project).items[0].metadata.name
    streamed_log_file = open("%s/streamed-operator.log" % (log_dir), "w+")
    streaming = subprocess.Popen("kubectl logs %s -f" %
                                 pod_name, stdout=streamed_log_file, stderr=streamed_log_file, shell=True, preexec_fn=os.setsid)

    test_workload.run(mode)

    pod_name = kubernetes.client.CoreV1Api().list_namespaced_pod(
        "default", watch=False, label_selector="sonartag="+project).items[0].metadata.name

    for i in range(num_apiservers):
        apiserver_name = "kube-apiserver-kind-control-plane" + \
            ("" if i == 0 else str(i + 1))
        apiserver_log = "apiserver%s.log" % (str(i + 1))
        os.system(
            "kubectl logs %s -n kube-system > %s/%s" % (apiserver_name, log_dir, apiserver_log))

    os.system(
        "docker cp kind-control-plane:/sonar-server/sonar-server.log %s/sonar-server.log" % (log_dir))

    os.system(
        "kubectl logs %s > %s/operator.log" % (pod_name, log_dir))
    os.killpg(streaming.pid, signal.SIGTERM)
    streamed_log_file.close()


def check_result(project, mode, stage, test_config, log_dir, data_dir, two_sided, node_ignore):
    if stage == "learn":
        for analysis_mode in ["time-travel", "obs-gap"]:
            analyze.analyze_trace(project, log_dir, analysis_mode,
                                  two_sided=two_sided, node_ignore=node_ignore)
        os.system("mkdir -p %s" % data_dir)
        os.system("cp %s %s" % (os.path.join(log_dir, "status.json"), os.path.join(
            data_dir, "status.json")))
        os.system("cp %s %s" % (os.path.join(log_dir, "side-effect.json"), os.path.join(
            data_dir, "side-effect.json")))
    else:
        if os.path.exists(test_config):
            open(os.path.join(log_dir, "config.yaml"),
                 "w").write(open(test_config).read())
        if mode == "vanilla":
            # TODO: We need another recording mode to only record digest without generating config
            pass
        else:
            learned_side_effect = json.load(open(os.path.join(
                data_dir, "side-effect.json")))
            learned_status = json.load(open(os.path.join(
                data_dir, "status.json")))
            server_log = os.path.join(log_dir, "sonar-server.log")
            testing_side_effect, testing_status = oracle.generate_digest(
                server_log)
            operator_log = os.path.join(log_dir, "streamed-operator.log")
            open(os.path.join(log_dir, "bug-report.txt"), "w").write(
                oracle.check(learned_side_effect, learned_status, testing_side_effect, testing_status, test_config, operator_log, server_log))
            json.dump(testing_side_effect, open(os.path.join(
                log_dir, "side-effect.json"), "w"), indent=4)
            json.dump(testing_status, open(os.path.join(
                log_dir, "status.json"), "w"), indent=4)


def run_test(project, mode, stage, test_workload, test_config, log_dir, docker_repo, docker_tag, num_apiservers, num_workers, data_dir, two_sided, node_ignore, phase):
    if phase == "all" or phase == "setup_only":
        setup_cluster(project, stage, mode, test_config,
                      docker_repo, docker_tag, num_apiservers, num_workers)
    if phase == "all" or phase == "workload_only":
        run_workload(project, mode, test_workload,
                     log_dir, num_apiservers)
    if phase == "all" or phase == "check_only":
        check_result(project, mode, stage, test_config,
                     log_dir, data_dir, two_sided, node_ignore)


def generate_learn_config(learn_config, project, mode, rate_limiter_enabled):
    learn_config_map = {}
    learn_config_map["stage"] = "learn"
    learn_config_map["mode"] = mode
    learn_config_map["crd-list"] = controllers.CRDs[project]
    if rate_limiter_enabled:
        learn_config_map["rate-limiter-enabled"] = "true"
        print("turn on rate limiter")
    else:
        learn_config_map["rate-limiter-enabled"] = "false"
        print("turn off rate limiter")
    # hardcode the interval to 3 seconds for now
    learn_config_map["rate-limiter-interval"] = "3"
    yaml.dump(learn_config_map, open(learn_config, "w"), sort_keys=False)


def run(test_suites, project, test, log_dir, mode, stage, config, docker, rate_limiter_enabled=False, phase="all"):
    suite = test_suites[project][test]
    data_dir = os.path.join("data", project, test, "learn")
    if phase == "all" or phase == "setup_only":
        os.system("rm -rf %s" % log_dir)
        os.system("mkdir -p %s" % log_dir)

    if stage == "learn":
        learn_config = os.path.join(log_dir, "learn.yaml")
        print("learn_config", learn_config)
        generate_learn_config(learn_config, project,
                              mode, rate_limiter_enabled)
        run_test(project, mode, stage, suite.workload,
                 learn_config, log_dir, docker, "learn", suite.num_apiservers, suite.num_workers, data_dir, suite.two_sided, suite.node_ignore, phase)
    else:
        if mode == "vanilla":
            blank_config = "config/none.yaml"
            run_test(project, mode, stage, suite.workload,
                     blank_config, log_dir, docker, mode, suite.num_apiservers, suite.num_workers, data_dir, suite.two_sided, suite.node_ignore, phase)
        else:
            test_config = config if config != "none" else suite.config
            test_config_to_use = os.path.join(
                log_dir, os.path.basename(test_config))
            os.system("cp %s %s" % (test_config, test_config_to_use))
            print("testing mode: %s config: %s" % (mode, test_config_to_use))
            run_test(project, mode, stage, suite.workload,
                     test_config_to_use, log_dir, docker, mode, suite.num_apiservers, suite.num_workers, data_dir, suite.two_sided, suite.node_ignore, phase)


def run_batch(project, test, dir, mode, stage, docker):
    assert stage == "test", "can only run batch mode under test stage"
    config_dir = os.path.join("log", project, test, "learn", mode)
    configs = [x for x in glob.glob(os.path.join(
        config_dir, "*.yaml")) if not "configmap" in x]
    print("configs", configs)
    for config in configs:
        num = os.path.basename(config).split(".")[0]
        log_dir = os.path.join(
            dir, project, test, "test", num)
        print("[sonar] config is %s" % config)
        print("[sonar] log dir is %s" % log_dir)
        try:
            run(controllers.test_suites, project,
                test, log_dir, mode, stage, config, docker)
        except Exception as err:
            print("error occurs during sieve run", config, err)


if __name__ == "__main__":
    s = time.time()
    usage = "usage: python3 sieve.py [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-p", "--project", dest="project",
                      help="specify PROJECT to test: cassandra-operator or zookeeper-operator", metavar="PROJECT", default="cassandra-operator")
    parser.add_option("-t", "--test", dest="test",
                      help="specify TEST to run", metavar="TEST", default="recreate")
    parser.add_option("-d", "--docker", dest="docker",
                      help="DOCKER repo that you have access", metavar="DOCKER", default=controllers.docker_repo)
    parser.add_option("-l", "--log", dest="log",
                      help="save to LOG", metavar="LOG", default="log")
    parser.add_option("-m", "--mode", dest="mode",
                      help="test MODE: vanilla, time-travel, obs-gap", metavar="MODE", default="none")
    parser.add_option("-c", "--config", dest="config",
                      help="test CONFIG", metavar="CONFIG", default="none")
    parser.add_option("-b", "--batch", dest="batch", action="store_true",
                      help="batch mode or not", default=False)
    parser.add_option("--phase", dest="phase",
                      help="run the PHASE: setup_only, workload_only, check_only or all", metavar="PHASE", default="all")
    parser.add_option("-s", "--stage", dest="stage",
                      help="STAGE: learn, test", default="test")
    parser.add_option("-r", "--rate_limiter", dest="rate_limiter", action="store_true",
                      help="use RATE LIMITER in learning stage or not", default=False)

    (options, args) = parser.parse_args()

    if options.mode == "none":
        if options.stage == "test":
            options.mode = controllers.test_suites[options.project][options.test].mode
        else:
            options.mode = "learn"

    assert options.stage in [
        "learn", "test"], "invalid stage option: %s" % options.stage
    assert options.mode in ["vanilla", "time-travel",
                            "obs-gap", "learn"], "invalid mode option: %s" % options.mode
    assert options.phase in ["all", "setup_only", "workload_only",
                             "check_only"], "invalid phase option: %s" % options.phase

    print("Running Sieve with stage: %s mode: %s..." %
          (options.stage, options.mode))

    if options.batch:
        run_batch(options.project, options.test,
                  "log-batch", options.mode, options.stage, options.docker)
    else:
        log_dir = os.path.join(options.log, options.project,
                               options.test, options.stage, options.mode)
        run(controllers.test_suites, options.project, options.test, log_dir,
            options.mode, options.stage, options.config, options.docker, options.rate_limiter, options.phase)
    print("total time: {} seconds".format(time.time() - s))
