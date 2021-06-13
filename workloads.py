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
        "scaledown-scaleup": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-cassandra-operator/test/cdc-2.yaml").wait_for_pod_status("cassandra-test-cluster-dc1-rack1-1", common.RUNNING)
        .cmd("kubectl patch CassandraDataCenter cassandra-datacenter --type merge -p='{\"spec\":{\"nodes\":1}}'").wait_for_pod_status("cassandra-test-cluster-dc1-rack1-1", common.TERMINATED).wait_for_pvc_status("data-volume-cassandra-test-cluster-dc1-rack1-1", common.TERMINATED)
        .cmd("kubectl patch CassandraDataCenter cassandra-datacenter --type merge -p='{\"spec\":{\"nodes\":2}}'").wait_for_pod_status("cassandra-test-cluster-dc1-rack1-1", common.RUNNING)
        .wait(50),
        "scaledown": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-cassandra-operator/test/cdc-2.yaml").wait_for_pod_status("cassandra-test-cluster-dc1-rack1-0", common.RUNNING).wait_for_pod_status("cassandra-test-cluster-dc1-rack1-1", common.RUNNING)
        .cmd("kubectl apply -f test-cassandra-operator/test/cdc-1.yaml").wait_for_pod_status("cassandra-test-cluster-dc1-rack1-1", common.TERMINATED)
        .wait(50),
    },
    "cass-operator": {
        "recreate": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-cass-operator/test/cdc-1.yaml").wait_for_pod_status("cluster1-sonar-cassandra-datacenter-default-sts-0", common.RUNNING)
        .cmd("kubectl delete CassandraDatacenter sonar-cassandra-datacenter").wait_for_pod_status("cluster1-sonar-cassandra-datacenter-default-sts-0", common.TERMINATED).wait_for_pvc_status("server-data-cluster1-sonar-cassandra-datacenter-default-sts-0", common.TERMINATED)
        .cmd("kubectl apply -f test-cass-operator/test/cdc-1.yaml").wait_for_pod_status("cluster1-sonar-cassandra-datacenter-default-sts-0", common.RUNNING)
        .wait(50),
    },
    "zookeeper-operator": {
        "recreate": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-zookeeper-operator/test/zkc-1.yaml").wait_for_pod_status("zookeeper-cluster-0", common.RUNNING)
        .cmd("kubectl delete ZookeeperCluster zookeeper-cluster").wait_for_pod_status("zookeeper-cluster-0", common.TERMINATED).wait_for_pvc_status("data-zookeeper-cluster-0", common.TERMINATED)
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
        "resize-pvc": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-rabbitmq-operator/test/rmqc-1.yaml").wait_for_pod_status("rabbitmq-cluster-server-0", common.RUNNING)
        .cmd("kubectl patch RabbitmqCluster rabbitmq-cluster --type merge -p='{\"spec\":{\"persistence\":{\"storage\":\"15Gi\"}}}'").wait_for_sts_storage_size("rabbitmq-cluster-server", "15Gi")
        .wait(50),
    },
    "mongodb-operator": {
        "recreate": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-mongodb-operator/test/cr.yaml").wait_for_pod_status("mongodb-cluster-rs0-2", common.RUNNING)
        .cmd("kubectl delete PerconaServerMongoDB mongodb-cluster").wait_for_pod_status("mongodb-cluster-rs0-2", common.TERMINATED).wait_for_pvc_status("mongod-data-mongodb-cluster-rs0-2", common.TERMINATED)
        .cmd("kubectl apply -f test-mongodb-operator/test/cr.yaml").wait_for_pod_status("mongodb-cluster-rs0-2", common.RUNNING)
        .wait(50),
        "disable-enable-shard": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-mongodb-operator/test/cr-shard.yaml").wait_for_pod_status("mongodb-cluster-rs0-2", common.RUNNING).wait_for_pod_status("mongodb-cluster-cfg-2", common.RUNNING)
        .cmd("kubectl patch PerconaServerMongoDB mongodb-cluster --type merge -p='{\"spec\":{\"sharding\":{\"enabled\":false}}}'").wait_for_pod_status("mongodb-cluster-cfg-2", common.TERMINATED)
        .cmd("kubectl patch PerconaServerMongoDB mongodb-cluster --type merge -p='{\"spec\":{\"sharding\":{\"enabled\":true}}}'").wait_for_pod_status("mongodb-cluster-cfg-2", common.RUNNING)
        .wait(50),
        "disable-enable-arbiter": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-mongodb-operator/test/cr-arbiter.yaml").wait_for_pod_status("mongodb-cluster-rs0-3", common.RUNNING).wait_for_pod_status("mongodb-cluster-rs0-arbiter-0", common.RUNNING)
        .cmd("kubectl patch PerconaServerMongoDB mongodb-cluster --type='json' -p='[{\"op\": \"replace\", \"path\": \"/spec/replsets/0/arbiter/enabled\", \"value\": false}]'").wait_for_pod_status("mongodb-cluster-rs0-arbiter-0", common.TERMINATED).wait_for_pod_status("mongodb-cluster-rs0-4", common.RUNNING)
        .cmd("kubectl patch PerconaServerMongoDB mongodb-cluster --type='json' -p='[{\"op\": \"replace\", \"path\": \"/spec/replsets/0/arbiter/enabled\", \"value\": true}]'").wait_for_pod_status("mongodb-cluster-rs0-arbiter-0", common.RUNNING).wait_for_pod_status("mongodb-cluster-rs0-4", common.TERMINATED)
        .wait(50),
        "enable-shard": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-mongodb-operator/test/cr.yaml").wait_for_pod_status("mongodb-cluster-rs0-2", common.RUNNING).wait_for_pod_status("mongodb-cluster-rs0-2", common.RUNNING)
        .cmd("kubectl patch PerconaServerMongoDB mongodb-cluster --type merge -p='{\"spec\":{\"sharding\":{\"enabled\":true}}}'").wait_for_pod_status("mongodb-cluster-cfg-2", common.RUNNING).wait_for_pod_status("mongodb-cluster-mongos-*", common.RUNNING)
        # TODO: in learning mode the digest sometimes is incorrect. We may need to have a recording mode for it
        .wait(50),
    },
    "xtradb-operator": {
        "recreate": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-xtradb-operator/test/cr.yaml").wait_for_pod_status("sonar-xtradb-cluster-pxc-2", common.RUNNING)
        .cmd("kubectl delete perconaxtradbcluster sonar-xtradb-cluster").wait_for_pod_status("sonar-xtradb-cluster-pxc-0", common.TERMINATED).wait_for_pod_status("sonar-xtradb-cluster-pxc-1", common.TERMINATED).wait_for_pod_status("sonar-xtradb-cluster-pxc-2", common.TERMINATED)
        .cmd("kubectl apply -f test-xtradb-operator/test/cr.yaml").wait_for_pod_status("sonar-xtradb-cluster-pxc-2", common.RUNNING)
        .wait(70),
        "disable-enable-haproxy": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-xtradb-operator/test/cr-haproxy-enabled.yaml").wait_for_pod_status("sonar-xtradb-cluster-pxc-2", common.RUNNING).wait_for_pod_status("sonar-xtradb-cluster-haproxy-0", common.RUNNING)
        .cmd("kubectl apply -f test-xtradb-operator/test/cr-haproxy-disabled.yaml").wait_for_pod_status("sonar-xtradb-cluster-haproxy-0", common.TERMINATED)
        .cmd("kubectl apply -f test-xtradb-operator/test/cr-haproxy-enabled.yaml").wait_for_pod_status("sonar-xtradb-cluster-haproxy-0", common.RUNNING)
        .wait(70),
        "disable-enable-proxysql": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-xtradb-operator/test/cr-proxysql-enabled.yaml").wait_for_pod_status("sonar-xtradb-cluster-pxc-2", common.RUNNING).wait_for_pod_status("sonar-xtradb-cluster-proxysql-0", common.RUNNING)
        .cmd("kubectl apply -f test-xtradb-operator/test/cr-proxysql-disabled.yaml").wait_for_pod_status("sonar-xtradb-cluster-proxysql-0", common.TERMINATED)
        .cmd("kubectl apply -f test-xtradb-operator/test/cr-proxysql-enabled.yaml").wait_for_pod_status("sonar-xtradb-cluster-proxysql-0", common.RUNNING)
        .wait(70),
    },
}
