import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
sieve_root = os.path.dirname(os.path.dirname(os.path.dirname(current)))
sys.path.append(sieve_root)

from sieve_test_driver.test_framework import new_built_in_workload
from sieve_common.common import RUNNING, TERMINATED

test_cases = {
    "recreate": new_built_in_workload(70)
    .cmd("kubectl apply -f examples/xtradb-operator/test/cr.yaml")
    .wait_for_pod_status("xtradb-cluster-pxc-2", RUNNING, 300)
    .cmd("kubectl delete perconaxtradbcluster xtradb-cluster")
    .wait_for_pod_status("xtradb-cluster-pxc-*", TERMINATED)
    .wait_for_pvc_status("datadir-xtradb-cluster-pxc-*", TERMINATED)
    .cmd("kubectl apply -f examples/xtradb-operator/test/cr.yaml")
    .wait_for_pod_status("xtradb-cluster-pxc-2", RUNNING, 300),
    "disable-enable-haproxy": new_built_in_workload(70)
    .cmd("kubectl apply -f examples/xtradb-operator/test/cr-haproxy-enabled.yaml")
    .wait_for_pod_status("xtradb-cluster-pxc-2", RUNNING, 300)
    .wait_for_pod_status("xtradb-cluster-haproxy-0", RUNNING)
    .cmd(
        'kubectl patch PerconaXtraDBCluster xtradb-cluster --type merge -p=\'{"spec":{"haproxy":{"enabled":false}}}\''
    )
    .wait_for_pod_status("xtradb-cluster-haproxy-0", TERMINATED)
    .cmd(
        'kubectl patch PerconaXtraDBCluster xtradb-cluster --type merge -p=\'{"spec":{"haproxy":{"enabled":true}}}\''
    )
    .wait_for_pod_status("xtradb-cluster-haproxy-0", RUNNING),
    "disable-enable-proxysql": new_built_in_workload(70)
    .cmd("kubectl apply -f examples/xtradb-operator/test/cr-proxysql-enabled.yaml")
    .wait_for_pod_status("xtradb-cluster-pxc-2", RUNNING, 300)
    .wait_for_pod_status("xtradb-cluster-proxysql-0", RUNNING)
    .cmd(
        'kubectl patch PerconaXtraDBCluster xtradb-cluster --type merge -p=\'{"spec":{"proxysql":{"enabled":false}}}\''
    )
    .wait_for_pod_status("xtradb-cluster-proxysql-0", TERMINATED)
    .cmd(
        'kubectl patch PerconaXtraDBCluster xtradb-cluster --type merge -p=\'{"spec":{"proxysql":{"enabled":true}}}\''
    )
    .wait_for_pod_status("xtradb-cluster-proxysql-0", RUNNING),
    "run-cert-manager": new_built_in_workload(70)
    .cmd(
        "kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v0.15.1/cert-manager.yaml --validate=false"
    )
    .wait_for_pod_status("cert-manager-webhook-*", RUNNING, namespace="cert-manager")
    .cmd("kubectl apply -f examples/xtradb-operator/test/cr.yaml")
    .wait_for_pod_status("xtradb-cluster-pxc-2", RUNNING, 250),
    "scaleup-scaledown": new_built_in_workload(70)
    .cmd("kubectl apply -f examples/xtradb-operator/test/cr.yaml")
    .wait_for_pod_status("xtradb-cluster-pxc-2", RUNNING, 300)
    .cmd(
        'kubectl patch PerconaXtraDBCluster xtradb-cluster --type merge -p=\'{"spec":{"pxc":{"size":5}}}\''
    )
    .wait_for_pod_status("xtradb-cluster-pxc-3", RUNNING)
    .wait_for_pod_status("xtradb-cluster-pxc-4", RUNNING)
    .cmd(
        'kubectl patch PerconaXtraDBCluster xtradb-cluster --type merge -p=\'{"spec":{"pxc":{"size":3}}}\''
    )
    .wait_for_pod_status("xtradb-cluster-pxc-3", TERMINATED, 300)
    .wait_for_pod_status("xtradb-cluster-pxc-4", TERMINATED, 300),
}

test_cases[sys.argv[1]].run(sys.argv[2], sys.argv[3])
