import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
sieve_root = os.path.dirname(os.path.dirname(os.path.dirname(current)))
sys.path.append(sieve_root)

from sieve_test_driver.test_framework import new_built_in_workload
from sieve_common.common import RUNNING, TERMINATED

test_cases = {
    "recreate": new_built_in_workload()
    .cmd("kubectl apply -f examples/cass-operator/test/cdc-1.yaml")
    .wait_for_pod_status("cluster1-cassandra-datacenter-default-sts-0", RUNNING)
    .cmd("kubectl delete CassandraDatacenter cassandra-datacenter")
    .wait_for_pod_status(
        "cluster1-cassandra-datacenter-default-sts-0",
        TERMINATED,
        200,
    )
    .wait_for_pvc_status(
        "server-data-cluster1-cassandra-datacenter-default-sts-0",
        TERMINATED,
        10,
    )
    .cmd("kubectl apply -f examples/cass-operator/test/cdc-1.yaml")
    .wait_for_pod_status("cluster1-cassandra-datacenter-default-sts-0", RUNNING)
    .wait_for_pod_status("create-pvc-*", TERMINATED),
    "scaledown-scaleup": new_built_in_workload()
    .cmd("kubectl apply -f examples/cass-operator/test/cdc-2.yaml")
    .wait_for_pod_status("cluster1-cassandra-datacenter-default-sts-1", RUNNING, 150)
    .cmd(
        'kubectl patch CassandraDatacenter cassandra-datacenter --type merge -p=\'{"spec":{"size": 1}}\''
    )
    .wait_for_pod_status("cluster1-cassandra-datacenter-default-sts-1", TERMINATED, 150)
    .cmd(
        'kubectl patch CassandraDatacenter cassandra-datacenter --type merge -p=\'{"spec":{"size": 2}}\''
    )
    .wait_for_pod_status("cluster1-cassandra-datacenter-default-sts-1", RUNNING, 150),
}

test_cases[sys.argv[1]].run(sys.argv[2])
