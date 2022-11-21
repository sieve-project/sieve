import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
sieve_root = os.path.dirname(os.path.dirname(os.path.dirname(current)))
sys.path.append(sieve_root)

from sieve_test_driver.test_framework import new_built_in_workload
from sieve_common.common import RUNNING, TERMINATED, NONEXIST, EXIST

test_cases = {
    "recreate": new_built_in_workload(70)
    .cmd("kubectl apply -f examples/yugabyte-operator/test/yb-1.yaml")
    .wait_for_pod_status("yb-master-2", RUNNING)
    .wait_for_pod_status("yb-tserver-2", RUNNING)
    .cmd("kubectl delete YBCluster example-ybcluster")
    .wait_for_pod_status("yb-master-0", TERMINATED)
    .wait_for_pod_status("yb-tserver-0", TERMINATED)
    .cmd("kubectl apply -f examples/yugabyte-operator/test/yb-1.yaml")
    .wait_for_pod_status("yb-master-2", RUNNING)
    .wait_for_pod_status("yb-tserver-2", RUNNING),
    "disable-enable-tls": new_built_in_workload()
    .cmd("kubectl apply -f examples/yugabyte-operator/test/yb-tls-enabled.yaml")
    .wait_for_pod_status("yb-master-2", RUNNING)
    .wait_for_pod_status("yb-tserver-2", RUNNING)
    .cmd(
        'kubectl patch YBCluster example-ybcluster --type merge -p=\'{"spec":{"tls":{"enabled":false}}}\''
    )
    .wait_for_secret_existence("yb-master-yugabyte-tls-cert", NONEXIST)
    .wait_for_secret_existence("yb-tserver-yugabyte-tls-cert", NONEXIST)
    .cmd(
        'kubectl patch YBCluster example-ybcluster --type merge -p=\'{"spec":{"tls":{"enabled":true}}}\''
    )
    .wait_for_secret_existence("yb-master-yugabyte-tls-cert", EXIST)
    .wait_for_secret_existence("yb-tserver-yugabyte-tls-cert", EXIST),
    "disable-enable-tuiport": new_built_in_workload(70)
    .cmd(
        "kubectl apply -f examples/yugabyte-operator/test/yb-tserverUIPort-enabled.yaml"
    )
    .wait_for_pod_status("yb-master-2", RUNNING)
    .wait_for_pod_status("yb-tserver-2", RUNNING)
    .cmd(
        'kubectl patch YBCluster example-ybcluster --type merge -p=\'{"spec":{"tserver":{"tserverUIPort": 0}}}\''
    )
    .wait_for_service_existence("yb-tserver-ui", NONEXIST)
    .cmd(
        'kubectl patch YBCluster example-ybcluster --type merge -p=\'{"spec":{"tserver":{"tserverUIPort": 7000}}}\''
    )
    .wait_for_service_existence("yb-tserver-ui", EXIST),
    "scaleup-scaledown-tserver": new_built_in_workload(70)
    .cmd("kubectl apply -f examples/yugabyte-operator/test/yb-1.yaml")
    .wait_for_pod_status("yb-master-2", RUNNING)
    .wait_for_pod_status("yb-tserver-2", RUNNING)
    .cmd(
        'kubectl patch YBCluster example-ybcluster --type merge -p=\'{"spec":{"tserver":{"replicas":4},"replicationFactor":4}}\''
    )
    .wait_for_pod_status("yb-tserver-3", RUNNING, 20)
    .cmd(
        'kubectl patch YBCluster example-ybcluster --type merge -p=\'{"spec":{"tserver":{"replicas":3},"replicationFactor":4}}\''
    ),
}

test_cases[sys.argv[1]].run(sys.argv[2])
