import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
sieve_root = os.path.dirname(os.path.dirname(os.path.dirname(current)))
sys.path.append(sieve_root)

from sieve_test_driver.test_framework import new_built_in_workload
from sieve_common.common import RUNNING, TERMINATED

test_cases = {
    "recreate": new_built_in_workload()
    .cmd("kubectl apply -f examples/cassandra-operator/test/cdc-1.yaml")
    .wait_for_pod_status("cassandra-test-cluster-dc1-rack1-0", RUNNING)
    .cmd("kubectl delete CassandraDataCenter cassandra-datacenter")
    .wait_for_pod_status("cassandra-test-cluster-dc1-rack1-0", TERMINATED, 10)
    .cmd("kubectl apply -f examples/cassandra-operator/test/cdc-1.yaml")
    .wait_for_pod_status("cassandra-test-cluster-dc1-rack1-0", RUNNING),
    "scaledown-scaleup": new_built_in_workload()
    .cmd("kubectl apply -f examples/cassandra-operator/test/cdc-2.yaml")
    .wait_for_pod_status("cassandra-test-cluster-dc1-rack1-1", RUNNING, 200)
    .cmd(
        'kubectl patch CassandraDataCenter cassandra-datacenter --type merge -p=\'{"spec":{"nodes":1}}\''
    )
    .wait_for_pod_status("cassandra-test-cluster-dc1-rack1-1", TERMINATED, 150)
    .wait_for_pvc_status(
        "data-volume-cassandra-test-cluster-dc1-rack1-1",
        TERMINATED,
        20,
    )
    .cmd(
        'kubectl patch CassandraDataCenter cassandra-datacenter --type merge -p=\'{"spec":{"nodes":2}}\''
    )
    .wait_for_pod_status("cassandra-test-cluster-dc1-rack1-1", RUNNING, 150),
}

test_cases[sys.argv[1]].run(sys.argv[2], sys.argv[3])
