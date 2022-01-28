import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
sieve_root = os.path.dirname(os.path.dirname(os.path.dirname(current)))
sys.path.append(sieve_root)

from sieve_test_driver.test_framework import new_built_in_workload
from sieve_common.common import RUNNING, TERMINATED

test_cases = {
    "recreate": new_built_in_workload()
    .cmd("kubectl apply -f examples/casskop-operator/test/cassandra-configmap-v1.yaml")
    .cmd("kubectl apply -f examples/casskop-operator/test/cc-1.yaml")
    .wait_for_pod_status("cassandra-cluster-dc1-rack1-0", RUNNING)
    .cmd("kubectl delete CassandraCluster cassandra-cluster")
    .wait_for_pod_status("cassandra-cluster-dc1-rack1-0", TERMINATED, soft_time_out=20)
    .cmd("kubectl apply -f examples/casskop-operator/test/cc-1.yaml")
    .wait_for_pod_status("cassandra-cluster-dc1-rack1-0", RUNNING),
    "reducepdb": new_built_in_workload(110)
    .cmd("kubectl apply -f examples/casskop-operator/test/cassandra-configmap-v1.yaml")
    .cmd("kubectl apply -f examples/casskop-operator/test/cc-2.yaml")
    .wait(60)
    .cmd("kubectl apply -f examples/casskop-operator/test/cc-1.yaml"),
    "scaledown-to-zero": new_built_in_workload()
    .cmd("kubectl apply -f examples/casskop-operator/test/cassandra-configmap-v1.yaml")
    .cmd("kubectl apply -f examples/casskop-operator/test/nodes-2.yaml")
    .wait_for_pod_status("cassandra-cluster-dc1-rack1-0", RUNNING)
    .wait_for_pod_status("cassandra-cluster-dc1-rack1-1", RUNNING)
    .cmd("kubectl apply -f examples/casskop-operator/test/nodes-1.yaml")
    .wait_for_pod_status("cassandra-cluster-dc1-rack1-0", RUNNING)
    .wait_for_pod_status("cassandra-cluster-dc1-rack1-1", TERMINATED)
    .cmd("kubectl apply -f examples/casskop-operator/test/nodes-0.yaml"),
}

test_cases[sys.argv[1]].run(sys.argv[2], sys.argv[3])
