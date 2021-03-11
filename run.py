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
            print("%s\t%s\t%s" % (pvc.metadata.name, pvc.status.phase, pvc.metadata.deletion_timestamp))
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

def cassandra_run(test_script, server_config, controller_config, apiserver_config, ha, restart, log_dir):
    os.system("rm -rf %s" % (log_dir))
    os.system("mkdir -p %s" % (log_dir))
    os.system("cp %s sonar-server/server.yaml" % (server_config))
    os.system("kind delete cluster")
    if ha:
        os.system("./setup.sh kind-ha.yaml")
    else:
        os.system("./setup.sh kind.yaml")

    time.sleep(60)
    if ha:
        time.sleep(20) # sleep 20 more seconds for HA mode since there are more nodes

    os.system("kubectl cp %s kube-apiserver-kind-control-plane:/sonar.yaml -n kube-system" % (apiserver_config))
    if ha:
        os.system("kubectl cp %s kube-apiserver-kind-control-plane2:/sonar.yaml -n kube-system" % (apiserver_config))
        # os.system("kubectl cp %s kube-apiserver-kind-control-plane3:/sonar.yaml -n kube-system" % (apiserver_config))
        # os.system("kubectl cp %s kube-apiserver-kind-control-plane4:/sonar.yaml -n kube-system" % (apiserver_config))
    time.sleep(5)
    os.system("kubectl apply -f test-cassandra-operator/config/crds.yaml")
    os.system("kubectl apply -f test-cassandra-operator/config/bundle.yaml")
    time.sleep(25)

    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    pod_name = core_v1.list_namespaced_pod(k8s_namespace, watch=False, label_selector="name=cassandra-operator").items[0].metadata.name
    api1_addr = "https://" + core_v1.list_node(watch=False, label_selector="kubernetes.io/hostname=kind-control-plane").items[0].status.addresses[0].address + ":6443"
    api2_addr = "https://" + core_v1.list_node(watch=False, label_selector="kubernetes.io/hostname=kind-control-plane2").items[0].status.addresses[0].address + ":6443"
    os.system("kubectl get CassandraDataCenter -s %s" % (api1_addr))
    os.system("kubectl get CassandraDataCenter -s %s" % (api2_addr))

    os.system("kubectl cp %s %s:/sonar.yaml" % (controller_config, pod_name))
    os.system("kubectl exec %s -- /bin/bash -c \"KUBERNETES_SERVICE_HOST=kind-control-plane KUBERNETES_SERVICE_PORT=6443 ./cassandra-operator &> operator1.log &\"" % (pod_name))

    org_dir = os.getcwd()
    os.chdir(os.path.join(org_dir, "test-cassandra-operator"))
    os.system("./%s %s" % (test_script, api1_addr))
    os.chdir(org_dir)

    os.system("kubectl logs kube-apiserver-kind-control-plane -n kube-system > %s/apiserver1.log" % (log_dir))
    if ha:
        os.system("kubectl logs kube-apiserver-kind-control-plane2 -n kube-system > %s/apiserver2.log" % (log_dir))
        # os.system("kubectl logs kube-apiserver-kind-control-plane3 -n kube-system > %s/apiserver3.log" % (log_dir))
        # os.system("kubectl logs kube-apiserver-kind-control-plane4 -n kube-system > %s/apiserver4.log" % (log_dir))
    os.system("docker cp kind-control-plane:/sonar-server/sonar-server.log %s/sonar-server.log" % (log_dir))
    os.system("kubectl cp %s:/operator1.log %s/operator1.log" % (pod_name, log_dir))
    if restart:
        os.system("kubectl cp %s:/operator2.log %s/operator2.log" % (pod_name, log_dir))

def cassandra_t1(normal):
    if normal:
        log_dir = "log/ca1/normal"
        test_config = blank_config
    else:
        log_dir = "log/ca1/faulty"
        test_config = "test-cassandra-operator/config/bug1.yaml"
    cassandra_run("test1.sh", test_config, test_config, blank_config, False, False, log_dir)

def cassandra_t2(normal):
    if normal:
        log_dir = "log/ca2/normal"
        test_config = blank_config
    else:
        log_dir = "log/ca2/faulty"
        test_config = "test-cassandra-operator/config/bug2.yaml"
    cassandra_run("test2.sh", test_config, blank_config, test_config, True, True, log_dir)

def cassandra_t3(normal):
    if normal:
        log_dir = "log/ca3/normal"
        test_config = blank_config
    else:
        log_dir = "log/ca3/faulty"
        test_config = "test-cassandra-operator/config/bug3.yaml"
    cassandra_run("test3.sh", test_config, blank_config, test_config, True, True, log_dir)

if __name__ == "__main__":
    usage = "usage: python3 test1.py -d [DIR]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-d", "--dir", dest="dir",
                  help="write report to DIR", metavar="DIR")

    (options, args) = parser.parse_args()
    if options.dir != None:
        log_dir = options.dir
    # os.makedirs(log_dir, exist_ok = True)
    print("dir is %s" % (log_dir))

    cassandra_t2(True)
    digest_normal = generate_digest()
    cassandra_t2(False)
    digest_faulty = generate_digest()
    compare_digest(digest_normal, digest_faulty)
