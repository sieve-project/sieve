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


def watch_crd(project, addrs):
    for addr in addrs:
        for crd in controllers.CRDs[project]:
            os.system("kubectl get %s -s %s" % (crd, addr))


def setup_cluster(project, mode, test_script, test_config, log_dir, docker_repo, docker_tag, cluster_config):
    os.system("rm -rf %s" % log_dir)
    os.system("mkdir -p %s" % log_dir)
    os.system("cp %s sonar-server/server.yaml" % test_config)
    os.system("kind delete cluster")

    os.system("./setup.sh %s %s %s" %
              (cluster_config, docker_repo, docker_tag))
    os.system("./bypass-balancer.sh")

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

    controllers.deploy[project](docker_repo, docker_tag)

    # Wait for project pod ready
    w = kubernetes.watch.Watch()
    for event in w.stream(core_v1.list_namespaced_pod, namespace="default", label_selector="sonartag="+project):
        if event['object'].status.phase == "Running":
            w.stop()

    pod_name = core_v1.list_namespaced_pod(
        "default", watch=False, label_selector="sonartag="+project).items[0].metadata.name

    container_num = len(core_v1.list_namespaced_pod("default", watch=False,
                        label_selector="sonartag="+project).items[0].status.container_statuses)
    # TODO: we should either make it configurable or give up the hacky approach
    container_flag = "" if container_num == 1 else "-c manager"

    api1_addr = "https://" + core_v1.list_node(
        watch=False, label_selector="kubernetes.io/hostname=kind-control-plane").items[0].status.addresses[0].address + ":6443"
    api2_addr = "https://" + core_v1.list_node(
        watch=False, label_selector="kubernetes.io/hostname=kind-control-plane2").items[0].status.addresses[0].address + ":6443"
    api3_addr = "https://" + core_v1.list_node(
        watch=False, label_selector="kubernetes.io/hostname=kind-control-plane3").items[0].status.addresses[0].address + ":6443"
    watch_crd(project, [api1_addr, api2_addr, api3_addr])

    os.system("kubectl cp %s %s %s:/sonar.yaml" %
              (container_flag, test_config, pod_name))
    os.system("kubectl exec %s %s -- /bin/bash -c \"KUBERNETES_SERVICE_HOST=kind-control-plane KUBERNETES_SERVICE_PORT=6443 %s &> operator.log &\"" %
              (container_flag, pod_name, controllers.command[project]))


def run_workload(project, mode, test_script, test_config, log_dir, docker_repo, docker_tag, cluster_config):
    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    pod_name = core_v1.list_namespaced_pod(
        "default", watch=False, label_selector="sonartag="+project).items[0].metadata.name
    container_num = len(core_v1.list_namespaced_pod("default", watch=False,
                        label_selector="sonartag="+project).items[0].status.container_statuses)
    # TODO: we should either make it configurable or give up the hacky approach
    container_flag = "" if container_num == 1 else "-c manager"

    org_dir = os.getcwd()
    os.chdir(controllers.test_dir[project])
    os.system("./%s %s" % (test_script, mode))
    os.chdir(org_dir)

    os.system(
        "kubectl logs kube-apiserver-kind-control-plane -n kube-system > %s/apiserver1.log" % (log_dir))
    os.system(
        "kubectl logs kube-apiserver-kind-control-plane2 -n kube-system > %s/apiserver2.log" % (log_dir))
    os.system(
        "kubectl logs kube-apiserver-kind-control-plane3 -n kube-system > %s/apiserver3.log" % (log_dir))
    os.system(
        "docker cp kind-control-plane:/sonar-server/sonar-server.log %s/sonar-server.log" % (log_dir))
    os.system("kubectl cp %s %s:/operator.log %s/operator.log" %
              (container_flag, pod_name, log_dir))


def post_process(project, mode, test_script, test_config, log_dir, docker_repo, docker_tag, cluster_config, data_dir, double_sides, run):
    if mode == "vanilla":
        pass
    elif mode == "learn":
        analyze.analyze_trace(project, log_dir, double_sides)
        os.system("mkdir -p %s" % data_dir)
        os.system("cp %s %s" % (os.path.join(log_dir, "status.json"), os.path.join(
            data_dir, "status.json")))
        os.system("cp %s %s" % (os.path.join(log_dir, "side-effect.json"), os.path.join(
            data_dir, "side-effect.json")))
    else:
        learned_side_effect = json.load(open(os.path.join(
            data_dir, "side-effect.json")))
        learned_status = json.load(open(os.path.join(
            data_dir, "status.json")))
        testing_side_effect, testing_status = oracle.generate_digest(
            os.path.join(log_dir, "sonar-server.log"))
        open(os.path.join(log_dir, "bug-report.txt"), "w").write(
            oracle.compare_digest(learned_side_effect, learned_status, testing_side_effect, testing_status, test_config))
        json.dump(testing_side_effect, open(os.path.join(
            log_dir, "side-effect.json"), "w"), indent=4)
        json.dump(testing_status, open(os.path.join(
            log_dir, "status.json"), "w"), indent=4)


def run_test(project, mode, test_script, test_config, log_dir, docker_repo, docker_tag, cluster_config, data_dir, double_sides, run):
    if run == "all" or run == "setup":
        setup_cluster(project, mode, test_script, test_config,
                      log_dir, docker_repo, docker_tag, cluster_config)
    if run == "all" or run == "workload":
        run_workload(project, mode, test_script, test_config,
                     log_dir, docker_repo, docker_tag, cluster_config)
        post_process(project, mode, test_script, test_config,
                     log_dir, docker_repo, docker_tag, cluster_config, data_dir, double_sides, run)


def run(test_suites, project, test, log_dir, mode, config, docker, run="all"):
    suite = test_suites[project][test]
    data_dir = os.path.join("data", project, test, "learn")
    assert run == "all" or run == "setup" or run == "workload", "wrong run option: %s" % run
    if mode == "vanilla":
        log_dir = os.path.join(log_dir, mode)
        blank_config = "config/none.yaml"
        run_test(project, mode, suite.workload,
                 blank_config, log_dir, docker, mode, suite.cluster_config, data_dir, suite.double_sides, run)
    elif mode == "learn":
        log_dir = os.path.join(log_dir, mode)
        learn_config = controllers.learning_configs[project]
        run_test(project, mode, suite.workload,
                 learn_config, log_dir, docker, mode, suite.cluster_config, data_dir, suite.double_sides, run)
    else:
        test_config = config if config != "none" else suite.config
        test_mode = mode if mode != "none" else suite.mode
        assert test_mode in controllers.testing_modes, "wrong mode option"
        print("testing mode: %s config: %s" % (test_mode, test_config))
        log_dir = os.path.join(log_dir, test_mode)
        run_test(project, test_mode, suite.workload,
                 test_config, log_dir, docker, test_mode, suite.cluster_config, data_dir, suite.double_sides, run)


def run_batch(project, test, dir, mode, docker):
    config_dir = os.path.join("log", project, test,
                              "learn", "generated-config")
    configs = glob.glob(os.path.join(config_dir, "*.yaml"))
    print("configs", configs)
    for config in configs:
        num = os.path.basename(config).split(".")[0]
        log_dir = os.path.join(
            dir, project, test, num)
        print("[sonar] config is %s" % config)
        print("[sonar] log dir is %s" % log_dir)
        run(controllers.test_suites, project,
            test, log_dir, mode, config, docker)


if __name__ == "__main__":
    s = time.time()
    usage = "usage: python3 run.py [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-p", "--project", dest="project",
                      help="specify PROJECT to test: cassandra-operator or zookeeper-operator", metavar="PROJECT", default="cassandra-operator")
    parser.add_option("-t", "--test", dest="test",
                      help="specify TEST to run", metavar="TEST", default="test2")
    parser.add_option("-d", "--docker", dest="docker",
                      help="DOCKER repo that you have access", metavar="DOCKER", default=controllers.docker_repo)
    parser.add_option("-l", "--log", dest="log",
                      help="save to LOG", metavar="LOG", default="log")
    parser.add_option("-m", "--mode", dest="mode",
                      help="test MODE: vanilla, learn, time-travel, sparse-read", metavar="MODE", default="none")
    parser.add_option("-c", "--config", dest="config",
                      help="test CONFIG", metavar="CONFIG", default="none")
    parser.add_option("-b", "--batch", dest="batch", action="store_true",
                      help="batch mode or not", default=False)
    parser.add_option("-r", "--run", dest="run",
                      help="RUN set_up only, workload only, or all", metavar="RUN", default="all")

    (options, args) = parser.parse_args()

    if options.batch:
        run_batch(options.project, options.test,
                  "log-batch", options.mode, options.docker)
    else:
        run(controllers.test_suites, options.project, options.test, os.path.join(
            options.log, options.project, options.test), options.mode, options.config, options.docker, options.run)
    print("total time: {} seconds".format(time.time() - s))
