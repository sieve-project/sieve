import test_framework
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
        .cmd("kubectl patch CassandraDataCenter cassandra-datacenter --type merge -p='{\"spec\":{\"nodes\":1}}'").wait_for_pod_status("cassandra-test-cluster-dc1-rack1-1", common.TERMINATED, 80).wait_for_pvc_status("data-volume-cassandra-test-cluster-dc1-rack1-1", common.TERMINATED, 0)
        .cmd("kubectl patch CassandraDataCenter cassandra-datacenter --type merge -p='{\"spec\":{\"nodes\":2}}'").wait_for_pod_status("cassandra-test-cluster-dc1-rack1-1", common.RUNNING)
        .wait(50),
        "scaledown": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-cassandra-operator/test/cdc-2.yaml").wait_for_pod_status("cassandra-test-cluster-dc1-rack1-0", common.RUNNING).wait_for_pod_status("cassandra-test-cluster-dc1-rack1-1", common.RUNNING)
        .cmd("kubectl apply -f test-cassandra-operator/test/cdc-1.yaml").wait_for_pod_status("cassandra-test-cluster-dc1-rack1-1", common.TERMINATED)
        .wait(50),
    },
    "casskop-operator": {
        "recreate": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-casskop-operator/test/cassandra-configmap-v1.yaml")
        .cmd("kubectl apply -f test-casskop-operator/test/cc-1.yaml").wait_for_pod_status("cassandra-cluster-dc1-rack1-0", common.RUNNING)
        .cmd("kubectl delete CassandraCluster cassandra-cluster").wait_for_pod_status("cassandra-cluster-dc1-rack1-0", common.TERMINATED)
        .cmd("kubectl apply -f test-casskop-operator/test/cc-1.yaml").wait_for_pod_status("cassandra-cluster-dc1-rack1-0", common.RUNNING)
        .wait(50),
        "reducepdb": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-casskop-operator/test/cassandra-configmap-v1.yaml")
        .cmd("kubectl apply -f test-casskop-operator/test/cc-2.yaml").wait(60)
        .cmd("kubectl apply -f test-casskop-operator/test/cc-1.yaml").wait(60)
        .wait(50),
        "nodesperrack": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-casskop-operator/test/cassandra-configmap-v1.yaml")
        .cmd("kubectl apply -f test-casskop-operator/test/nodes-2.yaml").wait_for_pod_status("cassandra-cluster-dc1-rack1-1", common.RUNNING)
        .cmd("kubectl apply -f test-casskop-operator/test/nodes-1.yaml").wait(10)
        .cmd("kubectl apply -f test-casskop-operator/test/nodes-0.yaml").wait(10)
        .wait(50),
        "scaledown": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-casskop-operator/test/cassandra-configmap-v1.yaml")
        # Init 3
        .cmd("kubectl apply -f test-casskop-operator/test/dc-3.yaml").wait(100)
        # Old 3, now 2, crash defer update cc. Now dc is 2, but old is still 3, and we crash the operator
        # Inside 10s, the operator should handle for the change, and resatrted after 10s
        .cmd("kubectl apply -f test-casskop-operator/test/dc-2.yaml").wait(10)
        # Issue this, and start the operator, see old = 3
        .cmd("kubectl apply -f test-casskop-operator/test/dc-1.yaml").wait(60)
        .wait(50),
    },
    "cass-operator": {
        "recreate": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-cass-operator/test/cdc-1.yaml").wait_for_pod_status("cluster1-cassandra-datacenter-default-sts-0", common.RUNNING)
        .cmd("kubectl delete CassandraDatacenter cassandra-datacenter").wait_for_pod_status("cluster1-cassandra-datacenter-default-sts-0", common.TERMINATED).wait_for_pvc_status("server-data-cluster1-cassandra-datacenter-default-sts-0", common.TERMINATED)
        .cmd("kubectl apply -f test-cass-operator/test/cdc-1.yaml").wait_for_pod_status("cluster1-cassandra-datacenter-default-sts-0", common.RUNNING)
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
        "scaledown-scaleup-obs": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-zookeeper-operator/test/zkc-2.yaml").wait_for_pod_status("zookeeper-cluster-1", common.RUNNING).wait(30)
        .cmd("kubectl patch ZookeeperCluster zookeeper-cluster --type merge -p='{\"spec\":{\"replicas\":1}}'").wait(55)
        .cmd("kubectl patch ZookeeperCluster zookeeper-cluster --type merge -p='{\"spec\":{\"replicas\":2}}'").wait(60)
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
        "scaleup-scaledown": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-rabbitmq-operator/test/rmqc-1.yaml").wait_for_pod_status("rabbitmq-cluster-server-0", common.RUNNING)
        .cmd("kubectl patch RabbitmqCluster rabbitmq-cluster --type merge -p='{\"spec\":{\"replicas\":3}}'").wait(10)
        .cmd("kubectl patch RabbitmqCluster rabbitmq-cluster --type merge -p='{\"spec\":{\"replicas\":2}}'").wait(10)
        .wait(50),
        "resize-pvc-atomic": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-rabbitmq-operator/test/rmqc-1.yaml").wait_for_pod_status("rabbitmq-cluster-server-0", common.RUNNING)
        # 10Gi -> 15Gi
        .cmd("kubectl patch RabbitmqCluster rabbitmq-cluster --type merge -p='{\"spec\":{\"persistence\":{\"storage\":\"15Gi\"}}}'").wait_for_sts_storage_size("rabbitmq-cluster-server", "15Gi")
        .wait(120),
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
        # "enable-shard": test_framework.new_built_in_workload()
        # .cmd("kubectl apply -f test-mongodb-operator/test/cr.yaml").wait_for_pod_status("mongodb-cluster-rs0-2", common.RUNNING).wait_for_pod_status("mongodb-cluster-rs0-2", common.RUNNING)
        # .cmd("kubectl patch PerconaServerMongoDB mongodb-cluster --type merge -p='{\"spec\":{\"sharding\":{\"enabled\":true}}}'").wait_for_pod_status("mongodb-cluster-cfg-2", common.RUNNING).wait_for_pod_status("mongodb-cluster-mongos-*", common.RUNNING)
        # TODO: in learning mode the digest sometimes is incorrect. We may need to have a recording mode for it
        # .wait(50),
    },
    "xtradb-operator": {
        "recreate": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-xtradb-operator/test/cr.yaml").wait_for_pod_status("xtradb-cluster-pxc-2", common.RUNNING)
        .cmd("kubectl delete perconaxtradbcluster xtradb-cluster").wait_for_pod_status("xtradb-cluster-pxc-0", common.TERMINATED).wait_for_pod_status("xtradb-cluster-pxc-1", common.TERMINATED).wait_for_pod_status("xtradb-cluster-pxc-2", common.TERMINATED)
        .cmd("kubectl apply -f test-xtradb-operator/test/cr.yaml").wait_for_pod_status("xtradb-cluster-pxc-2", common.RUNNING)
        .wait(70),
        "disable-enable-haproxy": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-xtradb-operator/test/cr-haproxy-enabled.yaml").wait_for_pod_status("xtradb-cluster-pxc-2", common.RUNNING).wait_for_pod_status("xtradb-cluster-haproxy-0", common.RUNNING)
        .cmd("kubectl apply -f test-xtradb-operator/test/cr-haproxy-disabled.yaml").wait_for_pod_status("xtradb-cluster-haproxy-0", common.TERMINATED)
        .cmd("kubectl apply -f test-xtradb-operator/test/cr-haproxy-enabled.yaml").wait_for_pod_status("xtradb-cluster-haproxy-0", common.RUNNING)
        .wait(70),
        "disable-enable-proxysql": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-xtradb-operator/test/cr-proxysql-enabled.yaml").wait_for_pod_status("xtradb-cluster-pxc-2", common.RUNNING).wait_for_pod_status("xtradb-cluster-proxysql-0", common.RUNNING)
        .cmd("kubectl apply -f test-xtradb-operator/test/cr-proxysql-disabled.yaml").wait_for_pod_status("xtradb-cluster-proxysql-0", common.TERMINATED)
        .cmd("kubectl apply -f test-xtradb-operator/test/cr-proxysql-enabled.yaml").wait_for_pod_status("xtradb-cluster-proxysql-0", common.RUNNING)
        .wait(70),
    },
    "yugabyte-operator": {
        "recreate": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-yugabyte-operator/test/yb-1.yaml").wait_for_pod_status("yb-master-0", common.RUNNING)
        .cmd("kubectl delete YBCluster example-ybcluster").wait_for_pod_status("yb-master-0", common.TERMINATED)
        .wait_for_pod_status("yb-master-1", common.TERMINATED).wait_for_pod_status("yb-master-2", common.TERMINATED)
        .cmd("kubectl apply -f test-yugabyte-operator/test/yb-1.yaml").wait_for_pod_status("yb-master-0", common.RUNNING)
        .wait(70),
        "disable-enable-tls": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-yugabyte-operator/test/yb-tls-enabled.yaml")
        .wait_for_pod_status("yb-master-2", common.RUNNING)
        .wait_for_pod_status("yb-tserver-2", common.RUNNING)
        .cmd("kubectl patch YBCluster example-ybcluster --type merge -p='{\"spec\":{\"tls\":{\"enabled\":false}}}'")
        .wait_for_secret_existence("yb-master-yugabyte-tls-cert", common.NONEXIST)
        .wait_for_secret_existence("yb-tserver-yugabyte-tls-cert", common.NONEXIST)
        .cmd("kubectl patch YBCluster example-ybcluster --type merge -p='{\"spec\":{\"tls\":{\"enabled\":true}}}'")
        .wait_for_secret_existence("yb-master-yugabyte-tls-cert", common.EXIST)
        .wait_for_secret_existence("yb-tserver-yugabyte-tls-cert", common.EXIST)
        .wait(70),
        "disable-enable-tserverUIPort": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-yugabyte-operator/test/yb-tserverUIPort-enabled.yaml")
        .wait_for_pod_status("yb-master-2", common.RUNNING)
        .wait_for_pod_status("yb-tserver-2", common.RUNNING)
        .cmd("kubectl patch YBCluster example-ybcluster --type merge -p='{\"spec\":{\"tserver\":{\"tserverUIPort\": 0}}}'")
        .wait_for_service_existence("yb-tserver-ui", common.NONEXIST)
        .cmd("kubectl patch YBCluster example-ybcluster --type merge -p='{\"spec\":{\"tserver\":{\"tserverUIPort\": 7000}}}'")
        .wait_for_service_existence("yb-tserver-ui", common.EXIST)
        .wait(70),
        "scaleup-scaledown-tserver": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-yugabyte-operator/test/yb-1.yaml")
        .wait_for_pod_status("yb-master-2", common.RUNNING)
        .wait_for_pod_status("yb-tserver-2", common.RUNNING)
        .cmd("kubectl patch YBCluster example-ybcluster --type merge -p='{\"spec\":{\"tserver\":{\"replicas\":4},\"replicationFactor\":4}}'")
        .wait_for_pod_status("yb-tserver-3", common.RUNNING, 20)
        .cmd("kubectl patch YBCluster example-ybcluster --type merge -p='{\"spec\":{\"tserver\":{\"replicas\":3},\"replicationFactor\":4}}'")
        .wait(70),
    },
    "nifikop-operator": {
        "change-config": test_framework.new_built_in_workload()
        .cmd("kubectl apply -f test-nifikop-operator/test/nc.yaml")
        .wait_for_pod_status("simplenifi-1-*", common.RUNNING)
        .cmd("kubectl apply -f test-nifikop-operator/test/nc1.yaml")
        .wait(30).wait_for_pod_status("simplenifi-1-*", common.RUNNING)
        .wait(60),
    }
}
