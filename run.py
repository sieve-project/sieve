import optparse
import os
import kubernetes
import enum
import time
import json
from analyze import analyzeTrace
from analyze import generateDigest

log_dir = "log"
k8s_namespace = "default"


blank_config = "config/none.yaml"
learn_config = "config/learn.yaml"


def compare_digest(digest_normal, digest_faulty):
    alarm = 0
    allKeys = set(digest_normal.keys()).union(digest_faulty.keys())
    for rtype in allKeys:
        if rtype not in digest_normal:
            print("[WARN] %s not in learned digest" % (rtype))
            alarm += 1
            continue
        elif rtype not in digest_faulty:
            print("[WARN] %s not in testing digest" % (rtype))
            alarm += 1
            continue
        else:
            for attr in digest_normal[rtype]:
                if digest_normal[rtype][attr] != digest_faulty[rtype][attr]:
                    print(
                        "[WARN] %s.%s inconsistent: learned %s, testing: %s" % (rtype, attr, str(digest_normal[rtype][attr]), str(digest_faulty[rtype][attr])))
                    alarm += 1
    if alarm != 0:
        print("[FIND BUG] # alarms: %d" % (alarm))


def run_test(project, test_script, server_config, controller_config, apiserver_config, ha, restart, log_dir):
    os.system("rm -rf %s" % (log_dir))
    os.system("mkdir -p %s" % (log_dir))
    os.system("cp %s sonar-server/server.yaml" % (server_config))
    os.system("kind delete cluster")
    if ha:
        os.system("./setup.sh kind-ha.yaml")
        os.system("./bypass-balancer.sh")
    else:
        os.system("./setup.sh kind.yaml")

    time.sleep(50)
    if ha:
        # sleep 40 more seconds for HA mode since there are more nodes
        time.sleep(40)

    os.system("kubectl cp %s kube-apiserver-kind-control-plane:/sonar.yaml -n kube-system" %
              (apiserver_config))
    if ha:
        os.system("kubectl cp %s kube-apiserver-kind-control-plane2:/sonar.yaml -n kube-system" %
                  (apiserver_config))
        os.system("kubectl cp %s kube-apiserver-kind-control-plane3:/sonar.yaml -n kube-system" %
                  (apiserver_config))

    time.sleep(5)
    if project == "cassandra-operator":
        os.system("kubectl apply -f test-cassandra-operator/config/crds.yaml")
        os.system("kubectl apply -f test-cassandra-operator/config/bundle.yaml")
        time.sleep(6)
    elif project == "zookeeper-operator":
        os.system("kubectl create -f test-zookeeper-operator/config/deploy/crds")
        os.system(
            "kubectl create -f test-zookeeper-operator/config/deploy/default_ns/rbac.yaml")
        os.system(
            "kubectl create -f test-zookeeper-operator/config/deploy/default_ns/operator.yaml")
        time.sleep(6)

    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    pod_name = core_v1.list_namespaced_pod(
        k8s_namespace, watch=False, label_selector="name="+project).items[0].metadata.name
    if ha:
        api2_addr = "https://" + core_v1.list_node(
            watch=False, label_selector="kubernetes.io/hostname=kind-control-plane2").items[0].status.addresses[0].address + ":6443"
        api3_addr = "https://" + core_v1.list_node(
            watch=False, label_selector="kubernetes.io/hostname=kind-control-plane3").items[0].status.addresses[0].address + ":6443"
        if project == "cassandra-operator":
            os.system("kubectl get CassandraDataCenter -s %s" % (api2_addr))
            os.system("kubectl get CassandraDataCenter -s %s" % (api3_addr))
        elif project == "zookeeper-operator":
            os.system("kubectl get ZookeeperCluster -s %s" % (api2_addr))
            os.system("kubectl get ZookeeperCluster -s %s" % (api3_addr))

    os.system("kubectl cp %s %s:/sonar.yaml" % (controller_config, pod_name))
    if project == "cassandra-operator":
        os.system("kubectl exec %s -- /bin/bash -c \"KUBERNETES_SERVICE_HOST=kind-control-plane KUBERNETES_SERVICE_PORT=6443 /cassandra-operator &> operator.log &\"" % (pod_name))
    elif project == "zookeeper-operator":
        os.system("kubectl exec %s -- /bin/bash -c \"KUBERNETES_SERVICE_HOST=kind-control-plane KUBERNETES_SERVICE_PORT=6443 /usr/local/bin/zookeeper-operator &> operator.log &\"" % (pod_name))

    org_dir = os.getcwd()
    os.chdir(os.path.join(org_dir, "test-" + project))
    os.system("./%s" % test_script)
    os.chdir(org_dir)

    os.system(
        "kubectl logs kube-apiserver-kind-control-plane -n kube-system > %s/apiserver1.log" % (log_dir))
    if ha:
        os.system(
            "kubectl logs kube-apiserver-kind-control-plane2 -n kube-system > %s/apiserver2.log" % (log_dir))
        os.system(
            "kubectl logs kube-apiserver-kind-control-plane3 -n kube-system > %s/apiserver3.log" % (log_dir))
    os.system(
        "docker cp kind-control-plane:/sonar-server/sonar-server.log %s/sonar-server.log" % (log_dir))
    os.system("kubectl cp %s:/operator.log %s/operator.log" %
              (pod_name, log_dir))


class Suite:
    def __init__(self, workload, config, ha, restart):
        self.workload = workload
        self.config = config
        self.ha = ha
        self.restart = restart


def generate_test_suites():
    test_suites = {}
    test_suites["cassandra-operator"] = {}
    test_suites["zookeeper-operator"] = {}
    test_suites["cassandra-operator"]["test1"] = Suite(
        "scaleDownCassandraDataCenter.sh", "test-cassandra-operator/config/bug1.yaml", False, False)
    test_suites["cassandra-operator"]["test2"] = Suite(
        "recreateCassandraDataCenter.sh", "test-cassandra-operator/config/bug2.yaml", True, True)
    test_suites["cassandra-operator"]["test3"] = Suite(
        "recreateCassandraDataCenter.sh", "test-cassandra-operator/config/bug3.yaml", True, True)
    test_suites["cassandra-operator"]["test4"] = Suite(
        "scaleDownUpCassandraDataCenter.sh", "test-cassandra-operator/config/bug4.yaml", True, True)
    test_suites["zookeeper-operator"]["test1"] = Suite(
        "recreateZookeeperCluster.sh", "test-zookeeper-operator/config/bug1.yaml", True, True)
    test_suites["zookeeper-operator"]["test2"] = Suite(
        "scaleDownUpZookeeperCluster.sh", "test-zookeeper-operator/config/bug2.yaml", True, True)
    return test_suites


def run(test_suites, project, test, dir, mode, config):
    suite = test_suites[project][test]
    test_config = suite.config
    if config != "none":
        test_config = config
    if mode == "normal":
        log_dir = os.path.join(dir, project, test, mode)
        run_test(project, suite.workload,
                 blank_config, blank_config, blank_config, suite.ha, suite.restart, log_dir)
    elif mode == "faulty":
        print("test config: %s" % test_config)
        log_dir = os.path.join(dir, project, test, mode)
        learned_digest = json.load(open(os.path.join(
            dir, project, test, "learn", "digest.json")))
        run_test(project, suite.workload,
                 test_config, test_config, test_config, suite.ha, suite.restart, log_dir)
        digest_faulty = generateDigest(
            os.path.join(log_dir, "operator.log"))
        compare_digest(learned_digest, digest_faulty)
        json.dump(digest_faulty, open(os.path.join(
            log_dir, "digest.json"), "w"), indent=4)
    elif mode == "learn":
        log_dir = os.path.join(dir, project, test, mode)
        run_test(project, suite.workload,
                 learn_config, learn_config, learn_config, suite.ha, suite.restart, log_dir)
        analyzeTrace(project, log_dir)
    else:
        assert False, "wrong mode option"


if __name__ == "__main__":
    usage = "usage: python3 run.py [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-p", "--project", dest="project",
                      help="specify PROJECT to test: cassandra-operator or zookeeper-operator", metavar="PROJECT", default="cassandra-operator")
    parser.add_option("-t", "--test", dest="test",
                      help="specify TEST to run", metavar="TEST", default="test2")
    parser.add_option("-d", "--dir", dest="dir",
                      help="write log to DIR", metavar="DIR", default="log")
    parser.add_option("-m", "--mode", dest="mode",
                      help="test MODE: normal, faulty, learn or compare", metavar="MODE", default="faulty")
    parser.add_option("-c", "--config", dest="config",
                      help="test CONFIG", metavar="CONFIG", default="none")

    (options, args) = parser.parse_args()
    dir = options.dir
    project = options.project
    test = options.test
    mode = options.mode
    config = options.config

    test_suites = generate_test_suites()
    run(test_suites, project, test, dir, mode, config)
