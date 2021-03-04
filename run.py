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
            # print("%s\t%s\t%s" % (i.metadata.name, i.status.phase, i.metadata.deletion_timestamp))
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
        print("%s has different length: %d %d" % (ktype, len(list1), len(list2)))
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
        print("%s has different terminating resources: %d %d" % (ktype, terminating1, terminating2))
        return 1
    return 0

def compare_digest(digest_normal, digest_faulty):
    alarm = 0
    for key in digest_normal.resources.keys():
        alarm += check_len(digest_normal.resources[key], digest_faulty.resources[key], key)
        alarm += check_deletion_timestamp(digest_normal.resources[key], digest_faulty.resources[key], key)
    if alarm != 0:
        print("[FIND BUG] # alarms: %d" % (alarm))


def cassandra_t1(normal):
    if normal:
        os.system("cp config/none.yaml sonar-server/server.yaml")
    else:
        os.system("cp config/sparse-read.yaml sonar-server/server.yaml")
    os.system("kind delete cluster")
    os.system("./setup.sh kind.yaml")

    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    os.system("kubectl apply -f cassandra-operator/crds.yaml")
    os.system("kubectl apply -f cassandra-operator/bundle.yaml")
    time.sleep(60)
    os.system("kubectl cp config/none.yaml kube-apiserver-kind-control-plane:/sonar.yaml -n kube-system")
    pod = core_v1.list_namespaced_pod(k8s_namespace, watch=False, label_selector="name=cassandra-operator").items[0]
    if normal:
        os.system("kubectl cp config/none.yaml %s:/sonar.yaml" % (pod.metadata.name))
    else:
        os.system("kubectl cp config/sparse-read.yaml %s:/sonar.yaml" % (pod.metadata.name))
    os.system("kubectl exec %s -- /bin/bash -c \"KUBERNETES_SERVICE_HOST=kind-control-plane KUBERNETES_SERVICE_PORT=6443 ./cassandra-operator &> operator.log &\"" % (pod.metadata.name))
    os.system("kubectl apply -f cassandra-operator/cdc-2.yaml")
    time.sleep(200)
    os.system("kubectl apply -f cassandra-operator/cdc-1.yaml")
    time.sleep(150)



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

    # os.system("./workload3.sh -d log-normal -n")
    cassandra_t1(True)
    digest_normal = generate_digest()
    
    # os.system("./workload3.sh -d log-faulty")
    cassandra_t1(False)
    digest_faulty = generate_digest()

    compare_digest(digest_normal, digest_faulty)
    # kubernetes.config.load_kube_config()
    # core_v1 = kubernetes.client.CoreV1Api()
    # ret = core_v1.list_namespaced_persistent_volume_claim("default", watch=False)
    # for i in ret.items:
    #     print("%s\t%s\t%s" % (i.metadata.name, i.status.phase, i.metadata.deletion_timestamp))


        
    





