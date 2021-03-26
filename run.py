import optparse
import os
import kubernetes
import enum
import time
import json
from analyze import analyzeTrace
from analyze import generateDigest
import controllers

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
                        "[WARN] %s.%s inconsistent: learned: %s, testing: %s" % (rtype, attr, str(digest_normal[rtype][attr]), str(digest_faulty[rtype][attr])))
                    alarm += 1
    if alarm != 0:
        print("[FIND BUG] # alarms: %d" % (alarm))


def watchCRD(project, addrs):
    for addr in addrs:
        for CRD in controllers.CRDs[project]:
            os.system("kubectl get %s -s %s" % (CRD, addr))


def run_test(project, mode, test_script, server_config, controller_config, apiserver_config, log_dir):
    os.system("rm -rf %s" % (log_dir))
    os.system("mkdir -p %s" % (log_dir))
    os.system("cp %s sonar-server/server.yaml" % (server_config))
    os.system("kind delete cluster")

    os.system("./setup.sh kind-ha.yaml")
    os.system("./bypass-balancer.sh")
    time.sleep(90)

    os.system("kubectl cp %s kube-apiserver-kind-control-plane:/sonar.yaml -n kube-system" %
              (apiserver_config))
    os.system("kubectl cp %s kube-apiserver-kind-control-plane2:/sonar.yaml -n kube-system" %
              (apiserver_config))
    os.system("kubectl cp %s kube-apiserver-kind-control-plane3:/sonar.yaml -n kube-system" %
              (apiserver_config))
    time.sleep(5)
    controllers.bootstrap[project]()
    time.sleep(5)

    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    pod_name = core_v1.list_namespaced_pod(
        k8s_namespace, watch=False, label_selector="name="+project).items[0].metadata.name

    api1_addr = "https://" + core_v1.list_node(
        watch=False, label_selector="kubernetes.io/hostname=kind-control-plane").items[0].status.addresses[0].address + ":6443"
    api2_addr = "https://" + core_v1.list_node(
        watch=False, label_selector="kubernetes.io/hostname=kind-control-plane2").items[0].status.addresses[0].address + ":6443"
    api3_addr = "https://" + core_v1.list_node(
        watch=False, label_selector="kubernetes.io/hostname=kind-control-plane3").items[0].status.addresses[0].address + ":6443"
    watchCRD(project, [api1_addr, api2_addr, api3_addr])

    os.system("kubectl cp %s %s:/sonar.yaml" % (controller_config, pod_name))
    os.system("kubectl exec %s -- /bin/bash -c \"KUBERNETES_SERVICE_HOST=kind-control-plane KUBERNETES_SERVICE_PORT=6443 %s &> operator.log &\"" %
              (pod_name, controllers.command[project]))

    org_dir = os.getcwd()
    os.chdir(os.path.join(org_dir, "test-" + project))
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
    os.system("kubectl cp %s:/operator.log %s/operator.log" %
              (pod_name, log_dir))


def run(test_suites, project, test, dir, mode, config):
    suite = test_suites[project][test]
    test_config = suite.config
    if config != "none":
        test_config = config
    if mode == "normal":
        log_dir = os.path.join(dir, project, test, mode)
        run_test(project, mode, suite.workload,
                 blank_config, blank_config, blank_config, log_dir)
    elif mode == "faulty":
        print("test config: %s" % test_config)
        log_dir = os.path.join(dir, project, test, mode)
        learned_digest = json.load(open(os.path.join(
            "data", project, test, "digest.json")))
        run_test(project, mode, suite.workload,
                 test_config, test_config, test_config, log_dir)
        digest_faulty = generateDigest(
            os.path.join(log_dir, "operator.log"))
        compare_digest(learned_digest, digest_faulty)
        json.dump(digest_faulty, open(os.path.join(
            log_dir, "digest.json"), "w"), indent=4)
    elif mode == "learn":
        log_dir = os.path.join(dir, project, test, mode)
        run_test(project, mode, suite.workload,
                 learn_config, learn_config, learn_config, log_dir)
        analyzeTrace(project, log_dir)
        os.system("cp %s %s" % (os.path.join(log_dir, "digest.json"), os.path.join(
            "data", project, test, "digest.json")))
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

    run(controllers.test_suites, project, test, dir, mode, config)
