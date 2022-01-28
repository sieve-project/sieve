import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
sieve_root = os.path.dirname(os.path.dirname(os.path.dirname(current)))
sys.path.append(sieve_root)

from sieve_test_driver.test_framework import new_built_in_workload
from sieve_common.common import RUNNING, TERMINATED

test_cases = {
    "recreate": new_built_in_workload()
    .cmd("kubectl apply -f examples/rabbitmq-operator/test/rmqc-1.yaml")
    .wait_for_pod_status("rabbitmq-cluster-server-0", RUNNING)
    .cmd("kubectl delete RabbitmqCluster rabbitmq-cluster")
    .wait_for_pod_status("rabbitmq-cluster-server-0", TERMINATED)
    .cmd("kubectl apply -f examples/rabbitmq-operator/test/rmqc-1.yaml")
    .wait_for_pod_status("rabbitmq-cluster-server-0", RUNNING),
    "scaleup-scaledown": new_built_in_workload(70)
    .cmd("kubectl apply -f examples/rabbitmq-operator/test/rmqc-1.yaml")
    .wait_for_pod_status("rabbitmq-cluster-server-0", RUNNING)
    .cmd(
        'kubectl patch RabbitmqCluster rabbitmq-cluster --type merge -p=\'{"spec":{"replicas":3}}\''
    )
    .wait_for_pod_status("rabbitmq-cluster-server-2", RUNNING)
    .cmd(
        'kubectl patch RabbitmqCluster rabbitmq-cluster --type merge -p=\'{"spec":{"replicas":2}}\''
    ),
    "resize-pvc": new_built_in_workload(80)
    .cmd("kubectl apply -f examples/rabbitmq-operator/test/rmqc-1.yaml")
    .wait_for_pod_status("rabbitmq-cluster-server-0", RUNNING)
    .cmd(
        'kubectl patch RabbitmqCluster rabbitmq-cluster --type merge -p=\'{"spec":{"persistence":{"storage":"15Gi"}}}\''
    )
    .wait_for_sts_storage_size("rabbitmq-cluster-server", "15Gi"),
}

test_cases[sys.argv[1]].run(sys.argv[2], sys.argv[3])
