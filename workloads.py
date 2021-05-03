import test_framework
import os
import common


workloads = {
    "cassandra-operator": {
        "recreate": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-cassandra-operator/test/cdc-1.yaml").wait_for_pod_status("cassandra-test-cluster-dc1-rack1-0", common.RUNNING)
        .cmd("kubectl delete CassandraDataCenter cassandra-datacenter").wait_for_pod_status("cassandra-test-cluster-dc1-rack1-0", common.TERMINATED)
        .cmd("kubectl apply -f test-cassandra-operator/test/cdc-1.yaml").wait_for_pod_status("cassandra-test-cluster-dc1-rack1-0", common.RUNNING)
        .wait(50),
    },
    "zookeeper-operator": {
        "recreate": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-zookeeper-operator/test/zkc-1.yaml").wait_for_pod_status("zookeeper-cluster-0", common.RUNNING)
        .cmd("kubectl delete ZookeeperCluster zookeeper-cluster").wait_for_pod_status("zookeeper-cluster-0", common.TERMINATED)
        .cmd("kubectl apply -f test-zookeeper-operator/test/zkc-1.yaml").wait_for_pod_status("zookeeper-cluster-0", common.RUNNING)
        .wait(50),
        "scaledown-scaleup": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-zookeeper-operator/test/zkc-2.yaml").wait_for_pod_status("zookeeper-cluster-1", common.RUNNING).wait(30)
        .cmd("kubectl patch ZookeeperCluster zookeeper-cluster --type merge -p='{\"spec\":{\"replicas\":1}}'").wait_for_pod_status("zookeeper-cluster-1", common.TERMINATED).wait_for_pvc_status("data-zookeeper-cluster-1", common.TERMINATED)
        .cmd("kubectl patch ZookeeperCluster zookeeper-cluster --type merge -p='{\"spec\":{\"replicas\":2}}'").wait_for_pod_status("zookeeper-cluster-1", common.RUNNING)
        .wait(50),
    },
    "rabbitmq-operator": {
        "recreate": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-rabbitmq-operator/test/rmqc-1.yaml").wait_for_pod_status("rabbitmq-cluster-server-0", common.RUNNING)
        .cmd("kubectl delete RabbitmqCluster rabbitmq-cluster").wait_for_pod_status("rabbitmq-cluster-server-0", common.TERMINATED)
        .cmd("kubectl apply -f test-rabbitmq-operator/test/rmqc-1.yaml").wait_for_pod_status("rabbitmq-cluster-server-0", common.RUNNING)
        .wait(50),
    },
}
