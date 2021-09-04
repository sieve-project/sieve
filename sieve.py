import optparse
import os
import kubernetes
import sieve_config
import time
import json
import glob
import analyze
import controllers
import oracle
import yaml
import subprocess
import signal
from common import cprint, bcolors, ok, sieve_modes


def watch_crd(project, addrs):
    for addr in addrs:
        for crd in controllers.CRDs[project]:
            os.system("kubectl get %s -s %s --ignore-not-found=true" %
                      (crd, addr))


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


def generate_kind_config(mode, num_apiservers, num_workers):
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


def prepare_sieve_server(test_config):
    os.system("cp %s sieve-server/server.yaml" % test_config)
    org_dir = os.getcwd()
    os.chdir("sieve-server")
    os.system("go mod tidy")
    os.system("go build")
    os.chdir(org_dir)
    os.system("docker cp sieve-server kind-control-plane:/sieve-server")


def start_sieve_server():
    os.system(
        "docker exec kind-control-plane bash -c 'cd /sieve-server && ./sieve-server &> sieve-server.log &'")


def stop_sieve_server():
    os.system("docker exec kind-control-plane bash -c 'pkill sieve-server'")


def setup_cluster(project, stage, mode, test_config, docker_repo, docker_tag, num_apiservers, num_workers, pvc_resize):
    os.system("kind delete cluster")
    os.system("./setup.sh %s %s %s" %
              (generate_kind_config(mode, num_apiservers, num_workers), docker_repo, docker_tag))
    # os.system("kubectl create namespace %s" % sieve_config["namespace"])
    # os.system("kubectl config set-context --current --namespace=%s" %
    #           sieve_config["namespace"])
    prepare_sieve_server(test_config)

    # when testing time-travel, we need to pause the apiserver
    # if workers talks to the paused apiserver, the whole cluster will be slowed down
    # so we need to redirect the workers to other apiservers
    if mode == sieve_modes.TIME_TRAVEL:
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
    print("We are loading image %s to kind nodes..." % (image))
    if os.WEXITSTATUS(os.system(kind_load_cmd)):
        print("Cannot load image %s locally, try to pull from remote" % (image))
        os.system("docker pull %s" % (image))
        os.system(kind_load_cmd)

    if pvc_resize:
        # Install csi provisioner
        os.system("cd csi-driver && ./install.sh")


def start_operator(project, docker_repo, docker_tag, num_apiservers):
    controllers.deploy[project](docker_repo, docker_tag)

    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()

    # Wait for project pod ready
    print("Wait for operator pod ready...")
    for tick in range(600):
        project_pod = core_v1.list_namespaced_pod(
            sieve_config.config["namespace"], watch=False, label_selector="sievetag="+project).items
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


def run_workload(project, mode, test_workload, test_config, log_dir, docker_repo, docker_tag, num_apiservers):
    cprint("Setting up Sieve server ...", bcolors.OKGREEN)
    start_sieve_server()
    ok("Sieve server set up")

    cprint("Deploying operator ...", bcolors.OKGREEN)
    start_operator(project, docker_repo, docker_tag, num_apiservers)
    ok("Operator deployed")

    kubernetes.config.load_kube_config()
    pod_name = kubernetes.client.CoreV1Api().list_namespaced_pod(
        sieve_config.config["namespace"], watch=False, label_selector="sievetag="+project).items[0].metadata.name
    streamed_log_file = open("%s/streamed-operator.log" % (log_dir), "w+")
    streaming = subprocess.Popen("kubectl logs %s -f" %
                                 pod_name, stdout=streamed_log_file, stderr=streamed_log_file, shell=True, preexec_fn=os.setsid)

    cprint("Running test workload ...", bcolors.OKGREEN)
    test_workload.run(mode)
    ok("Test workload finished")

    pod_name = kubernetes.client.CoreV1Api().list_namespaced_pod(
        sieve_config.config["namespace"], watch=False, label_selector="sievetag="+project).items[0].metadata.name

    for i in range(num_apiservers):
        apiserver_name = "kube-apiserver-kind-control-plane" + \
            ("" if i == 0 else str(i + 1))
        apiserver_log = "apiserver%s.log" % (str(i + 1))
        os.system(
            "kubectl logs %s -n kube-system > %s/%s" % (apiserver_name, log_dir, apiserver_log))

    os.system(
        "docker cp kind-control-plane:/sieve-server/sieve-server.log %s/sieve-server.log" % (log_dir))

    os.system(
        "kubectl logs %s > %s/operator.log" % (pod_name, log_dir))
    os.killpg(streaming.pid, signal.SIGTERM)
    streamed_log_file.close()
    stop_sieve_server()


def check_result(project, mode, stage, test_config, log_dir, data_dir, two_sided, node_ignore):
    if stage == "learn":
        analyze.analyze_trace(
            project, log_dir, two_sided=two_sided, node_ignore=node_ignore)
        os.system("mkdir -p %s" % data_dir)
        os.system("cp %s %s" % (os.path.join(log_dir, "status.json"), os.path.join(
            data_dir, "status.json")))
        os.system("cp %s %s" % (os.path.join(log_dir, "side-effect.json"), os.path.join(
            data_dir, "side-effect.json")))
        os.system("cp %s %s" % (os.path.join(log_dir, "resources.json"), os.path.join(
            data_dir, "resources.json")))
    else:
        if os.path.exists(test_config):
            open(os.path.join(log_dir, "config.yaml"),
                 "w").write(open(test_config).read())
        if mode == sieve_modes.VANILLIA:
            # TODO: We need another recording mode to only record digest without generating config
            pass
        else:
            learned_side_effect = json.load(open(os.path.join(
                data_dir, "side-effect.json")))
            learned_status = json.load(open(os.path.join(
                data_dir, "status.json")))
            resources_path = os.path.join(data_dir, "resources.json")
            learned_resources = json.load(
                open(resources_path)) if os.path.isfile(resources_path) else None
            server_log = os.path.join(log_dir, "sieve-server.log")
            testing_side_effect, testing_status, testing_resources = oracle.generate_digest(
                server_log)
            operator_log = os.path.join(log_dir, "streamed-operator.log")
            open(os.path.join(log_dir, "bug-report.txt"), "w").write(
                oracle.check(learned_side_effect, learned_status, learned_resources, testing_side_effect, testing_status, testing_resources, test_config, operator_log, server_log))
            json.dump(testing_side_effect, open(os.path.join(
                log_dir, "side-effect.json"), "w"), indent=4)
            json.dump(testing_status, open(os.path.join(
                log_dir, "status.json"), "w"), indent=4)
            json.dump(testing_resources, open(os.path.join(
                log_dir, "resources.json"), "w"), indent=4)


def run_test(project, mode, stage, test_workload, test_config, log_dir, docker_repo, docker_tag, num_apiservers, num_workers, pvc_resize, data_dir, two_sided, node_ignore, phase):
    if phase == "all" or phase == "setup_only":
        setup_cluster(project, stage, mode, test_config,
                      docker_repo, docker_tag, num_apiservers, num_workers, pvc_resize)
    if phase == "all" or phase == "workload_only" or phase == "workload_and_check":
        run_workload(project, mode, test_workload, test_config,
                     log_dir, docker_repo, docker_tag, num_apiservers)
    if phase == "all" or phase == "check_only" or phase == "workload_and_check":
        check_result(project, mode, stage, test_config,
                     log_dir, data_dir, two_sided, node_ignore)


def generate_learn_config(learn_config, project, mode, rate_limiter_enabled):
    learn_config_map = {}
    learn_config_map["stage"] = "learn"
    learn_config_map["mode"] = mode
    learn_config_map["crd-list"] = controllers.CRDs[project]
    if rate_limiter_enabled:
        learn_config_map["rate-limiter-enabled"] = "true"
        print("Turn on rate limiter")
    else:
        learn_config_map["rate-limiter-enabled"] = "false"
        print("Turn off rate limiter")
    # hardcode the interval to 3 seconds for now
    learn_config_map["rate-limiter-interval"] = "3"
    yaml.dump(learn_config_map, open(learn_config, "w"), sort_keys=False)


def run(test_suites, project, test, log_dir, mode, stage, config, docker, rate_limiter_enabled=False, phase="all"):
    suite = test_suites[project][test]
    data_dir = os.path.join("data", project, test, "learn")
    print("Log dir: %s" % log_dir)
    if phase == "all" or phase == "setup_only":
        os.system("rm -rf %s" % log_dir)
        os.system("mkdir -p %s" % log_dir)

    if stage == "learn":
        learn_config = os.path.join(log_dir, "learn.yaml")
        print("Learning stage with config %s" % learn_config)
        generate_learn_config(learn_config, project,
                              mode, rate_limiter_enabled)
        run_test(project, mode, stage, suite.workload,
                 learn_config, log_dir, docker, stage, suite.num_apiservers, suite.num_workers, suite.pvc_resize, data_dir, suite.two_sided, suite.node_ignore, phase)
    else:
        if mode == sieve_modes.VANILLIA:
            blank_config = "config/none.yaml"
            run_test(project, mode, stage, suite.workload,
                     blank_config, log_dir, docker, mode, suite.num_apiservers, suite.num_workers, suite.pvc_resize, data_dir, suite.two_sided, suite.node_ignore, phase)
        else:
            test_config = config if config != "none" else suite.config
            print("Testing with config: %s" % test_config)
            test_config_to_use = os.path.join(
                log_dir, os.path.basename(test_config))
            os.system("cp %s %s" % (test_config, test_config_to_use))
            if mode == sieve_modes.TIME_TRAVEL:
                suite.num_apiservers = 3
            run_test(project, mode, stage, suite.workload,
                     test_config_to_use, log_dir, docker, mode, suite.num_apiservers, suite.num_workers, suite.pvc_resize, data_dir, suite.two_sided, suite.node_ignore, phase)


def run_batch(project, test, dir, mode, stage, docker):
    assert stage == "test", "can only run batch mode under test stage"
    config_dir = os.path.join("log", project, test, "learn", "learn", mode)
    configs = [x for x in glob.glob(os.path.join(
        config_dir, "*.yaml")) if not "configmap" in x]
    print("Configs", configs)
    for config in configs:
        num = os.path.basename(config).split(".")[0]
        log_dir = os.path.join(
            dir, project, test, stage, mode + "-batch", num)
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
                      help="test MODE: vanilla, time-travel, obs-gap, atom-vio", metavar="MODE", default="none")
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

    if options.mode == "obs-gap":
        options.mode = sieve_modes.OBS_GAP
    elif options.mode == "atom-vio":
        options.mode = sieve_modes.ATOM_VIO

    if options.stage == "learn":
        options.mode = "learn"

    if options.mode == "none" and options.stage == "test":
        options.mode = controllers.test_suites[options.project][options.test].mode

    assert options.stage in [
        "learn", "test"], "invalid stage option: %s" % options.stage
    assert options.mode in [sieve_modes.VANILLIA, sieve_modes.TIME_TRAVEL,
                            sieve_modes.OBS_GAP, sieve_modes.ATOM_VIO, "learn"], "invalid mode option: %s" % options.mode
    assert options.phase in ["all", "setup_only", "workload_only",
                             "check_only", "workload_and_check"], "invalid phase option: %s" % options.phase

    print("Running Sieve with %s: %s..." %
          (options.stage, options.mode))

    if options.batch:
        run_batch(options.project, options.test,
                  options.log, options.mode, options.stage, options.docker)
    else:
        log_dir = os.path.join(options.log, options.project,
                               options.test, options.stage, options.mode)
        run(controllers.test_suites, options.project, options.test, log_dir,
            options.mode, options.stage, options.config, options.docker, options.rate_limiter, options.phase)
    print("Total time: {} seconds".format(time.time() - s))
