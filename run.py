import optparse
import os
import kubernetes
import enum
import time

log_dir = "log"
k8s_namespace = "default"


POD = "pod"
PVC = "persistentVolumeClaim"
DEPLOYMENT = "deployment"
STS = "statefulSet"

ktypes = [POD, PVC, DEPLOYMENT, STS]

blank_config = "config/none.yaml"
learn_config = "config/learn.yaml"

class Digest:
    def __init__(self, core_v1, apps_v1):
        self.resources = {}
        for ktype in ktypes:
            # print("list for " + ktype)
            self.resources[ktype] = []
        for pod in core_v1.list_namespaced_pod(k8s_namespace, watch=False).items:
            self.resources[POD].append(pod)
        for pvc in core_v1.list_namespaced_persistent_volume_claim(k8s_namespace, watch=False).items:
            self.resources[PVC].append(pvc)
            # print("%s\t%s\t%s" % (pvc.metadata.name, pvc.status.phase, pvc.metadata.deletion_timestamp))
        for dp in apps_v1.list_namespaced_deployment(k8s_namespace, watch=False).items:
            self.resources[DEPLOYMENT].append(dp)
        for sts in apps_v1.list_namespaced_stateful_set(k8s_namespace, watch=False).items:
            self.resources[STS].append(sts)

def generate_digest():
    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    apps_v1 = kubernetes.client.AppsV1Api()
    digest = Digest(core_v1, apps_v1)
    return digest

def log_digest(digest):
    print("We should generate a json for the digest", digest)

def check_len(list1, list2, ktype):
    if len(list1) != len(list2):
        print("%s has different length: normal: %d faulty: %d" % (ktype, len(list1), len(list2)))
        return 1
    return 0

def check_deletion_timestamp(list1, list2, ktype):
    terminating1 = 0
    for item in list1:
        # print("dts of %s is %s" % (item.metadata.name, item.metadata.deletion_timestamp))
        if item.metadata.deletion_timestamp != None:
            terminating1 += 1
    terminating2 = 0
    for item in list2:
        # print("dts of %s is %s" % (item.metadata.name, item.metadata.deletion_timestamp))
        if item.metadata.deletion_timestamp != None:
            terminating2 += 1
    if terminating1 != terminating2:
        print("%s has different terminating resources: normal: %d faulty: %d" % (ktype, terminating1, terminating2))
        return 1
    return 0

def compare_digest(digest_normal, digest_faulty):
    alarm = 0
    for key in digest_normal.resources.keys():
        alarm += check_len(digest_normal.resources[key], digest_faulty.resources[key], key)
        alarm += check_deletion_timestamp(digest_normal.resources[key], digest_faulty.resources[key], key)
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

    time.sleep(60)
    if ha:
        time.sleep(20) # sleep 20 more seconds for HA mode since there are more nodes

    os.system("kubectl cp %s kube-apiserver-kind-control-plane:/sonar.yaml -n kube-system" % (apiserver_config))
    if ha:
        os.system("kubectl cp %s kube-apiserver-kind-control-plane2:/sonar.yaml -n kube-system" % (apiserver_config))

    time.sleep(5)
    if project == "cassandra-operator":
        os.system("kubectl apply -f test-cassandra-operator/config/crds.yaml")
        os.system("kubectl apply -f test-cassandra-operator/config/bundle.yaml")
        time.sleep(6)
    elif project == "zookeeper-operator":
        os.system("kubectl create -f test-zookeeper-operator/config/deploy/crds")
        os.system("kubectl create -f test-zookeeper-operator/config/deploy/default_ns/rbac.yaml")
        os.system("kubectl create -f test-zookeeper-operator/config/deploy/default_ns/operator.yaml")
        time.sleep(6)

    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    pod_name = core_v1.list_namespaced_pod(k8s_namespace, watch=False, label_selector="name="+project).items[0].metadata.name
    if ha:
        api2_addr = "https://" + core_v1.list_node(watch=False, label_selector="kubernetes.io/hostname=kind-control-plane2").items[0].status.addresses[0].address + ":6443"
        if project == "cassandra-operator":
            os.system("kubectl get CassandraDataCenter -s %s" % (api2_addr))
        elif project == "zookeeper-operator":
            os.system("kubectl get ZookeeperCluster -s %s" % (api2_addr))

    os.system("kubectl cp %s %s:/sonar.yaml" % (controller_config, pod_name))
    if project == "cassandra-operator":
        os.system("kubectl exec %s -- /bin/bash -c \"KUBERNETES_SERVICE_HOST=kind-control-plane KUBERNETES_SERVICE_PORT=6443 /cassandra-operator &> operator1.log &\"" % (pod_name))
    elif project == "zookeeper-operator":
        os.system("kubectl exec %s -- /bin/bash -c \"KUBERNETES_SERVICE_HOST=kind-control-plane KUBERNETES_SERVICE_PORT=6443 /usr/local/bin/zookeeper-operator &> operator1.log &\"" % (pod_name))

    org_dir = os.getcwd()
    os.chdir(os.path.join(org_dir, "test-" + project))
    os.system("./%s" % test_script)
    os.chdir(org_dir)

    os.system("kubectl logs kube-apiserver-kind-control-plane -n kube-system > %s/apiserver1.log" % (log_dir))
    if ha:
        os.system("kubectl logs kube-apiserver-kind-control-plane2 -n kube-system > %s/apiserver2.log" % (log_dir))
    os.system("docker cp kind-control-plane:/sonar-server/sonar-server.log %s/sonar-server.log" % (log_dir))
    os.system("kubectl cp %s:/operator1.log %s/operator1.log" % (pod_name, log_dir))
    if restart:
        os.system("kubectl cp %s:/operator2.log %s/operator2.log" % (pod_name, log_dir))

def cassandra_t1(log, normal):
    if mode == "normal":
        log_dir = os.path.join(log, "ca1/normal")
        server_config = blank_config
        controller_config = blank_config
        apiserver_config = blank_config
    elif mode == "faulty":
        log_dir = os.path.join(log, "ca1/faulty")
        server_config = "test-cassandra-operator/config/bug1.yaml"
        controller_config = "test-cassandra-operator/config/bug1.yaml"
        apiserver_config = "test-cassandra-operator/config/bug1.yaml"
    elif mode == "learn":
        log_dir = os.path.join(log, "ca1/learn")
        server_config = learn_config
        controller_config = learn_config
        apiserver_config = learn_config
    run_test("cassandra-operator", "scaleDownCassandraDataCenter.sh", server_config, controller_config, apiserver_config, False, False, log_dir)

def cassandra_t2(log, mode):
    if mode == "normal":
        log_dir = os.path.join(log, "ca2/normal")
        server_config = blank_config
        controller_config = blank_config
        apiserver_config = blank_config
    elif mode == "faulty":
        log_dir = os.path.join(log, "ca2/faulty")
        server_config = "test-cassandra-operator/config/bug2.yaml"
        controller_config = "test-cassandra-operator/config/bug2.yaml"
        apiserver_config = "test-cassandra-operator/config/bug2.yaml"
    elif mode == "learn":
        log_dir = os.path.join(log, "ca2/learn")
        server_config = learn_config
        controller_config = learn_config
        apiserver_config = learn_config
    run_test("cassandra-operator", "recreateCassandraDataCenter.sh", server_config, controller_config, apiserver_config, True, True, log_dir)

def cassandra_t3(log, mode):
    if mode == "normal":
        log_dir = os.path.join(log, "ca3/normal")
        server_config = blank_config
        controller_config = blank_config
        apiserver_config = blank_config
    elif mode == "faulty":
        log_dir = os.path.join(log, "ca3/faulty")
        server_config = "test-cassandra-operator/config/bug3.yaml"
        controller_config = "test-cassandra-operator/config/bug3.yaml"
        apiserver_config = "test-cassandra-operator/config/bug3.yaml"
    elif mode == "learn":
        log_dir = os.path.join(log, "ca3/learn")
        server_config = learn_config
        controller_config = learn_config
        apiserver_config = learn_config
    run_test("cassandra-operator", "recreateCassandraDataCenter.sh", server_config, controller_config, apiserver_config, True, True, log_dir)

def zookeeper_t1(log, normal):
    if mode == "normal":
        log_dir = os.path.join(log, "zk1/normal")
        server_config = blank_config
        controller_config = blank_config
        apiserver_config = blank_config
    elif mode == "faulty":
        log_dir = os.path.join(log, "zk1/faulty")
        server_config = "test-zookeeper-operator/config/bug1.yaml"
        controller_config = "test-zookeeper-operator/config/bug1.yaml"
        apiserver_config = "test-zookeeper-operator/config/bug1.yaml"
    elif mode == "learn":
        log_dir = os.path.join(log, "zk1/learn")
        server_config = learn_config
        controller_config = learn_config
        apiserver_config = learn_config
    run_test("zookeeper-operator", "recreateZookeeperCluster.sh", server_config, controller_config, apiserver_config, True, True, log_dir)

def generate_test_suites():
    test_suites = {}
    test_suites["cassandra-operator"] = {}
    test_suites["zookeeper-operator"] = {}
    test_suites["cassandra-operator"]["test1"] = cassandra_t1
    test_suites["cassandra-operator"]["test2"] = cassandra_t2
    test_suites["cassandra-operator"]["test3"] = cassandra_t3
    test_suites["zookeeper-operator"]["test1"] = zookeeper_t1
    return test_suites

def run(test_suites, project, test, dir, mode):
    test = test_suites[project][test]
    if mode == "generate":
        test(dir, "normal")
        digest_normal = generate_digest()
        log_digest(digest_normal)
    elif mode == "compare":
        test(dir, "normal")
        digest_normal = generate_digest()
        log_digest(digest_normal)
        test(dir, "faulty")
        digest_faulty = generate_digest()
        compare_digest(digest_normal, digest_faulty)
    elif mode == "learn":
        test(dir, "learn")
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
                  help="test MODE: generate or compare", metavar="MODE", default="compare")

    (options, args) = parser.parse_args()
    dir = options.dir
    project = options.project
    test = options.test
    mode = options.mode

    test_suites = generate_test_suites()
    run(test_suites, project, test, dir, mode)
