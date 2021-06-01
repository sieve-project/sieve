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


def kind_config(num_workers):
    # we should generate the kind config automatically
    if num_workers == 2:
        return "kind-ha.yaml"
    elif num_workers == 3:
        return "kind-ha-3w.yaml"
    elif num_workers == 4:
        return "kind-ha-4w.yaml"
    elif num_workers == 5:
        return "kind-ha-5w.yaml"
    else:
        assert False


def redirect_if_necessary(mode, num_workers):
    # TODO: we may also need to redirect the controller-managers and schedulers
    if mode != "time-travel":
        return
    redirect_workers(mode, num_workers)


def redirect_workers(mode, num_workers):
    target_master = controllers.front_runner
    for i in range(num_workers):
        worker = "kind-worker" + (str(i+1) if i > 0 else "")
        os.system("docker exec %s bash -c \"sed -i 's/kind-external-load-balancer/%s/g' /etc/kubernetes/kubelet.conf\"" %
                  (worker, target_master))
        os.system("docker exec %s bash -c \"systemctl restart kubelet\"" % worker)


def setup_cluster(project, mode, learn, test_workload, test_config, log_dir, docker_repo, docker_tag, num_workers):
    os.system("rm -rf %s" % log_dir)
    os.system("mkdir -p %s" % log_dir)
    os.system("cp %s sonar-server/server.yaml" % test_config)
    os.system("kind delete cluster")

    os.system("./setup.sh %s %s %s" %
              (kind_config(num_workers), docker_repo, docker_tag))
    redirect_if_necessary(mode, num_workers)
    os.system("./bypass-balancer.sh")

    configmap = generate_configmap(test_config)
    os.system("kubectl apply -f %s" % configmap)

    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()

    # Then we wait apiservers to be ready
    apiserver_list = ['kube-apiserver-kind-control-plane',
                      'kube-apiserver-kind-control-plane2', 'kube-apiserver-kind-control-plane3']

    while True:
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
    w = kubernetes.watch.Watch()
    for event in w.stream(core_v1.list_namespaced_pod, namespace="default", label_selector="sonartag="+project):
        if event['object'].status.phase == "Running":
            w.stop()

    api1_addr = "https://" + core_v1.list_node(
        watch=False, label_selector="kubernetes.io/hostname=kind-control-plane").items[0].status.addresses[0].address + ":6443"
    api2_addr = "https://" + core_v1.list_node(
        watch=False, label_selector="kubernetes.io/hostname=kind-control-plane2").items[0].status.addresses[0].address + ":6443"
    api3_addr = "https://" + core_v1.list_node(
        watch=False, label_selector="kubernetes.io/hostname=kind-control-plane3").items[0].status.addresses[0].address + ":6443"
    watch_crd(project, [api1_addr, api2_addr, api3_addr])


def run_workload(project, mode, learn, test_workload, test_config, log_dir, docker_repo, docker_tag, num_workers):
    kubernetes.config.load_kube_config()
    pod_name = kubernetes.client.CoreV1Api().list_namespaced_pod(
        "default", watch=False, label_selector="sonartag="+project).items[0].metadata.name
    streamed_log_file = open("%s/streamed-operator.log" % (log_dir), "w+")
    streaming = subprocess.Popen("kubectl logs %s -f" %
                                 pod_name, stdout=streamed_log_file, stderr=streamed_log_file, shell=True, preexec_fn=os.setsid)

    test_workload.run(mode)

    pod_name = kubernetes.client.CoreV1Api().list_namespaced_pod(
        "default", watch=False, label_selector="sonartag="+project).items[0].metadata.name

    os.system(
        "kubectl logs kube-apiserver-kind-control-plane -n kube-system > %s/apiserver1.log" % (log_dir))
    os.system(
        "kubectl logs kube-apiserver-kind-control-plane2 -n kube-system > %s/apiserver2.log" % (log_dir))
    os.system(
        "kubectl logs kube-apiserver-kind-control-plane3 -n kube-system > %s/apiserver3.log" % (log_dir))
    os.system(
        "docker cp kind-control-plane:/sonar-server/sonar-server.log %s/sonar-server.log" % (log_dir))
    os.system(
        "kubectl logs %s > %s/operator.log" % (pod_name, log_dir))
    os.killpg(streaming.pid, signal.SIGTERM)
    streamed_log_file.close()


def pre_process(project, mode, learn, test_config):
    if learn:
        learn_config = {}
        learn_config["stage"] = "learn"
        learn_config["mode"] = mode
        learn_config["crd-list"] = controllers.CRDs[project]
        yaml.dump(learn_config, open(test_config, "w"), sort_keys=False)


def post_process(project, mode, learn, test_workload, test_config, log_dir, docker_repo, docker_tag, num_workers, data_dir, two_sided, run):
    if learn:
        analyze.analyze_trace(project, log_dir, mode, two_sided=two_sided)
        os.system("mkdir -p %s" % data_dir)
        os.system("cp %s %s" % (os.path.join(log_dir, "status.json"), os.path.join(
            data_dir, "status.json")))
        os.system("cp %s %s" % (os.path.join(log_dir, "side-effect.json"), os.path.join(
            data_dir, "side-effect.json")))
    else:
        if mode == "vanilla":
            # TODO: We need another recording mode to only record digest without generating config
            pass
        elif mode == "time-travel":
            learned_side_effect = json.load(open(os.path.join(
                data_dir, "side-effect.json")))
            learned_status = json.load(open(os.path.join(
                data_dir, "status.json")))
            testing_side_effect, testing_status = oracle.generate_digest(
                os.path.join(log_dir, "sonar-server.log"))
            operator_log = os.path.join(log_dir, "streamed-operator.log")
            open(os.path.join(log_dir, "bug-report.txt"), "w").write(
                oracle.check(learned_side_effect, learned_status, testing_side_effect, testing_status, test_config, operator_log))
            json.dump(testing_side_effect, open(os.path.join(
                log_dir, "side-effect.json"), "w"), indent=4)
            json.dump(testing_status, open(os.path.join(
                log_dir, "status.json"), "w"), indent=4)
        elif mode == "obs-gap":
            learned_side_effect = json.load(open(os.path.join(
                data_dir, "side-effect.json")))
            learned_status = json.load(open(os.path.join(
                data_dir, "status.json")))
            testing_side_effect, testing_status = oracle.generate_digest(
                os.path.join(log_dir, "sonar-server.log"))
            operator_log = os.path.join(log_dir, "streamed-operator.log")
            open(os.path.join(log_dir, "bug-report.txt"), "w").write(
                oracle.check(learned_side_effect, learned_status, testing_side_effect, testing_status, test_config, operator_log))
            json.dump(testing_side_effect, open(os.path.join(
                log_dir, "side-effect.json"), "w"), indent=4)
            json.dump(testing_status, open(os.path.join(
                log_dir, "status.json"), "w"), indent=4)



def run_test(project, mode, learn, test_workload, test_config, log_dir, docker_repo, docker_tag, num_workers, data_dir, two_sided, run):
    if run == "all" or run == "setup":
        pre_process(project, mode, learn, test_config)
        setup_cluster(project, mode, learn, test_workload, test_config,
                      log_dir, docker_repo, docker_tag, num_workers)
    if run == "all" or run == "workload":
        run_workload(project, mode, learn, test_workload, test_config,
                     log_dir, docker_repo, docker_tag, num_workers)
        post_process(project, mode, learn, test_workload, test_config,
                     log_dir, docker_repo, docker_tag, num_workers, data_dir, two_sided, run)


def run(test_suites, project, test, log_dir, mode, learn, config, docker, run="all"):
    suite = test_suites[project][test]
    data_dir = os.path.join("data", project, test, "learn")
    assert run == "all" or run == "setup" or run == "workload", "wrong run option: %s" % run

    if learn:
        log_dir = os.path.join(log_dir, mode)
        learn_config = os.path.join(
            controllers.test_dir[project], "test", "learn.yaml")
        run_test(project, mode, learn, suite.workload,
                 learn_config, log_dir, docker, "learn", suite.num_workers, data_dir, suite.two_sided, run)
    else:
        if mode == "vanilla":
            log_dir = os.path.join(log_dir, mode)
            blank_config = "config/none.yaml"
            run_test(project, mode, learn, suite.workload,
                    blank_config, log_dir, docker, mode, suite.num_workers, data_dir, suite.two_sided, run)
        else:
            test_config = config if config != "none" else suite.config
            print("testing mode: %s config: %s" % (mode, test_config))
            log_dir = os.path.join(log_dir, mode)
            run_test(project, mode, learn, suite.workload,
                    test_config, log_dir, docker, mode, suite.num_workers, data_dir, suite.two_sided, run)


def run_batch(project, test, dir, mode, learn, docker):
    assert not learn, "cannot run batch mode under learn stage"
    config_dir = os.path.join("log", project, "learn", test, mode, "generated-config")
    configs = [x for x in glob.glob(os.path.join(config_dir, "*.yaml")) if not "configmap" in x]
    print("configs", configs)
    for config in configs:
        num = os.path.basename(config).split(".")[0]
        log_dir = os.path.join(
            dir, project, "test", test, num)
        print("[sonar] config is %s" % config)
        print("[sonar] log dir is %s" % log_dir)
        try:
            run(controllers.test_suites, project,
                test, log_dir, mode, learn, config, docker)
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
                      help="test MODE: vanilla, time-travel, sparse-read", metavar="MODE", default="none")
    parser.add_option("-c", "--config", dest="config",
                      help="test CONFIG", metavar="CONFIG", default="none")
    parser.add_option("-b", "--batch", dest="batch", action="store_true",
                      help="batch mode or not", default=False)
    parser.add_option("-r", "--run", dest="run",
                      help="RUN set_up only, workload only, or all", metavar="RUN", default="all")
    parser.add_option("-n", "--learn", action="store_true", dest="learn", help="run sieve in learning mode", default=False)

    (options, args) = parser.parse_args()

    # For backward compatibility
    if options.mode in ["learn", "none"]:
        if options.mode == "learn":
            options.learn = True
        suite = controllers.test_suites[options.project][options.test]
        options.mode = suite.mode
        
    assert options.mode in controllers.testing_modes, "wrong mode option"

    stage = "learn" if options.learn else "test"
    print("Running Sieve on %s stage with %s mode..."%(stage, options.mode))

    if options.batch:
        run_batch(options.project, options.test,
                  "log-batch", options.mode, options.learn, options.docker)
    else:
        run(controllers.test_suites, options.project, options.test, os.path.join(
            options.log, options.project, stage, options.test), options.mode, options.learn, options.config, options.docker, options.run)
    print("total time: {} seconds".format(time.time() - s))
