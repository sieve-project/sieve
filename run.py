import optparse
import os
import kubernetes
import enum
import time
import json
import glob
from analyze import analyze_trace
from analyze import generate_digest
import controllers


def compare_map(learned_map, testing_map, map_type):
    alarm = 0
    all_keys = set(learned_map.keys()).union(
        testing_map.keys())
    bug_report = "[BUG REPORT] %s\n" % map_type
    for rtype in all_keys:
        if rtype not in learned_map:
            bug_report += "[ERROR] %s not in learning %s digest\n" % (
                rtype, map_type)
            alarm += 1
            continue
        elif rtype not in testing_map:
            bug_report += "[ERROR] %s not in testing %s digest\n" % (
                rtype, map_type)
            alarm += 1
            continue
        else:
            for attr in learned_map[rtype]:
                if attr not in testing_map[rtype]:
                    print("[WARN] attr: %s not int rtype: %s: " %
                          (attr, rtype), testing_map[rtype])
                    continue
                if learned_map[rtype][attr] != testing_map[rtype][attr]:
                    level = "WARN" if attr == "update" else "ERROR"
                    alarm += 0 if attr == "update" else 1
                    bug_report += "[%s] %s.%s inconsistent: learning: %s, testing: %s\n" % (
                        level, rtype, attr, str(learned_map[rtype][attr]), str(testing_map[rtype][attr]))
    return alarm, bug_report


def compare_digest(learned_side_effect, learned_status, testing_side_effect, testing_status):
    alarm_side_effect, bug_report_side_effect = compare_map(
        learned_side_effect, testing_side_effect, "side effect")
    alarm_status, bug_report_status = compare_map(
        learned_status, testing_status, "status")
    alarm = alarm_side_effect + alarm_status
    bug_report = bug_report_side_effect + bug_report_status
    if alarm != 0:
        bug_report += "[BUGGY] # alarms: %d\n" % (alarm)
    print(bug_report)
    return bug_report


def watch_crd(project, addrs):
    for addr in addrs:
        for crd in controllers.CRDs[project]:
            os.system("kubectl get %s -s %s" % (crd, addr))


def run_test(project, mode, test_script, server_config, controller_config, apiserver_config, log_dir, docker_repo, docker_tag, cluster_config):
    os.system("rm -rf %s" % log_dir)
    os.system("mkdir -p %s" % log_dir)
    os.system("cp %s sonar-server/server.yaml" % server_config)
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
                  (apiserver_config, apiserver))

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
    # Assume the container name is called "manager"
    container_flag = "" if container_num == 1 else "-c manager"

    api1_addr = "https://" + core_v1.list_node(
        watch=False, label_selector="kubernetes.io/hostname=kind-control-plane").items[0].status.addresses[0].address + ":6443"
    api2_addr = "https://" + core_v1.list_node(
        watch=False, label_selector="kubernetes.io/hostname=kind-control-plane2").items[0].status.addresses[0].address + ":6443"
    api3_addr = "https://" + core_v1.list_node(
        watch=False, label_selector="kubernetes.io/hostname=kind-control-plane3").items[0].status.addresses[0].address + ":6443"
    watch_crd(project, [api1_addr, api2_addr, api3_addr])

    os.system("kubectl cp %s %s %s:/sonar.yaml" %
              (container_flag, controller_config, pod_name))
    os.system("kubectl exec %s %s -- /bin/bash -c \"KUBERNETES_SERVICE_HOST=kind-control-plane KUBERNETES_SERVICE_PORT=6443 %s &> operator.log &\"" %
              (container_flag, pod_name, controllers.command[project]))

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


def run(test_suites, project, test, log_dir, mode, config, docker):
    suite = test_suites[project][test]
    data_dir = os.path.join("data", project, test, "learn")
    if mode == "vanilla":
        log_dir = os.path.join(log_dir, mode)
        blank_config = "config/none.yaml"
        run_test(project, mode, suite.workload,
                 blank_config, blank_config, blank_config, log_dir, docker, mode, suite.cluster_config)
    elif mode == "learn":
        log_dir = os.path.join(log_dir, mode)
        learn_config = controllers.learning_configs[project]
        run_test(project, mode, suite.workload,
                 learn_config, learn_config, learn_config, log_dir, docker, mode, suite.cluster_config)
        analyze_trace(project, log_dir, suite.double_sides)
        os.system("mkdir -p %s" % data_dir)
        os.system("cp %s %s" % (os.path.join(log_dir, "status.json"), os.path.join(
            data_dir, "status.json")))
        os.system("cp %s %s" % (os.path.join(log_dir, "side-effect.json"), os.path.join(
            data_dir, "side-effect.json")))
        # os.system("cp %s %s" % (os.path.join(log_dir, "sonar-server.log"), os.path.join(
        #     data_dir, "sonar-server.log")))
    else:
        test_config = config if config != "none" else suite.config
        test_mode = mode if mode != "none" else suite.mode
        assert test_mode in controllers.testing_modes, "wrong mode option"
        print("testing mode: %s config: %s" % (test_mode, test_config))
        log_dir = os.path.join(log_dir, test_mode)
        learned_side_effect = json.load(open(os.path.join(
            data_dir, "side-effect.json")))
        learned_status = json.load(open(os.path.join(
            data_dir, "status.json")))
        run_test(project, test_mode, suite.workload,
                 test_config, test_config, test_config, log_dir, docker, test_mode, suite.cluster_config)
        testing_side_effect, testing_status = generate_digest(
            os.path.join(log_dir, "operator.log"))
        open(os.path.join(log_dir, "bug-report.txt"), "w").write(
            compare_digest(learned_side_effect, learned_status, testing_side_effect, testing_status))
        json.dump(testing_side_effect, open(os.path.join(
            log_dir, "side-effect.json"), "w"), indent=4)
        json.dump(testing_status, open(os.path.join(
            log_dir, "status.json"), "w"), indent=4)


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

    (options, args) = parser.parse_args()

    if options.batch:
        run_batch(options.project, options.test,
                  "log-batch", options.mode, options.docker)
    else:
        run(controllers.test_suites, options.project, options.test, os.path.join(
            options.log, options.project, options.test), options.mode, options.config, options.docker)
    print("total time: {} seconds".format(time.time() - s))
