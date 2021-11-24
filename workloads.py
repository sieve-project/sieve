from sieve_test_driver.test_framework import new_built_in_workload
from sieve_common.common import RUNNING, TERMINATED, NONEXIST, EXIST


workloads = {
    "cassandra-operator": {
        "recreate": new_built_in_workload()
        .cmd("kubectl apply -f examples/cassandra-operator/test/cdc-1.yaml")
        .wait_for_pod_status("cassandra-test-cluster-dc1-rack1-0", RUNNING)
        .cmd("kubectl delete CassandraDataCenter cassandra-datacenter")
        .wait_for_pod_status("cassandra-test-cluster-dc1-rack1-0", TERMINATED, 10)
        .cmd("kubectl apply -f examples/cassandra-operator/test/cdc-1.yaml")
        .wait_for_pod_status("cassandra-test-cluster-dc1-rack1-0", RUNNING)
        .wait(50),
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
            10,
        )
        .cmd(
            'kubectl patch CassandraDataCenter cassandra-datacenter --type merge -p=\'{"spec":{"nodes":2}}\''
        )
        .wait_for_pod_status("cassandra-test-cluster-dc1-rack1-1", RUNNING)
        .wait(50),
    },
    "casskop-operator": {
        "recreate": new_built_in_workload()
        .cmd(
            "kubectl apply -f examples/casskop-operator/test/cassandra-configmap-v1.yaml"
        )
        .cmd("kubectl apply -f examples/casskop-operator/test/cc-1.yaml")
        .wait_for_pod_status("cassandra-cluster-dc1-rack1-0", RUNNING)
        .cmd("kubectl delete CassandraCluster cassandra-cluster")
        .wait_for_pod_status(
            "cassandra-cluster-dc1-rack1-0", TERMINATED, soft_time_out=20
        )
        .cmd("kubectl apply -f examples/casskop-operator/test/cc-1.yaml")
        .wait_for_pod_status("cassandra-cluster-dc1-rack1-0", RUNNING)
        .wait(50),
        # TODO: use wait_for
        "reducepdb": new_built_in_workload()
        .cmd(
            "kubectl apply -f examples/casskop-operator/test/cassandra-configmap-v1.yaml"
        )
        .cmd("kubectl apply -f examples/casskop-operator/test/cc-2.yaml")
        .wait(60)
        .cmd("kubectl apply -f examples/casskop-operator/test/cc-1.yaml")
        .wait(60)
        .wait(50),
        "scaledown-to-zero": new_built_in_workload()
        .cmd(
            "kubectl apply -f examples/casskop-operator/test/cassandra-configmap-v1.yaml"
        )
        .cmd("kubectl apply -f examples/casskop-operator/test/nodes-2.yaml")
        .wait_for_pod_status("cassandra-cluster-dc1-rack1-0", RUNNING)
        .wait_for_pod_status("cassandra-cluster-dc1-rack1-1", RUNNING)
        .cmd("kubectl apply -f examples/casskop-operator/test/nodes-1.yaml")
        .wait_for_pod_status("cassandra-cluster-dc1-rack1-0", RUNNING)
        .wait_for_pod_status("cassandra-cluster-dc1-rack1-1", TERMINATED)
        .cmd("kubectl apply -f examples/casskop-operator/test/nodes-0.yaml")
        .wait(50),
        # TODO(wenqing): Please fix this test case. As hinted in the operator log, we have to first set nodePerRack to 0 before resizing the dc
        # "scaledown": new_built_in_workload()
        # .cmd("kubectl apply -f examples/casskop-operator/test/cassandra-configmap-v1.yaml")
        # .cmd("kubectl apply -f examples/casskop-operator/test/dc-3.yaml")
        # .wait_for_pod_status("cassandra-cluster-dc1-rack1-0", RUNNING)
        # .wait_for_pod_status("cassandra-cluster-dc2-rack1-0", RUNNING)
        # .wait_for_pod_status("cassandra-cluster-dc3-rack1-0", RUNNING)
        # .cmd("kubectl apply -f examples/casskop-operator/test/dc-2.yaml")
        # .wait_for_pod_status("cassandra-cluster-dc3-rack1-0", TERMINATED, 10)
        # .cmd("kubectl apply -f examples/casskop-operator/test/dc-1.yaml")
        # .wait_for_pod_status("cassandra-cluster-dc2-rack1-0", TERMINATED, 60)
        # .wait(50),
    },
    "cass-operator": {
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
        .wait_for_pod_status("create-pvc-*", TERMINATED)
        .wait(50),
        "scaledown-scaleup": new_built_in_workload()
        .cmd("kubectl apply -f examples/cass-operator/test/cdc-2.yaml")
        .wait_for_pod_status(
            "cluster1-cassandra-datacenter-default-sts-1", RUNNING, 150
        )
        .cmd(
            'kubectl patch CassandraDatacenter cassandra-datacenter --type merge -p=\'{"spec":{"size": 1}}\''
        )
        .wait_for_pod_status(
            "cluster1-cassandra-datacenter-default-sts-1", TERMINATED, 150
        )
        .cmd(
            'kubectl patch CassandraDatacenter cassandra-datacenter --type merge -p=\'{"spec":{"size": 2}}\''
        )
        .wait_for_pod_status(
            "cluster1-cassandra-datacenter-default-sts-1", RUNNING, 150
        )
        .wait(50),
    },
    "zookeeper-operator": {
        "recreate": new_built_in_workload()
        .cmd("kubectl apply -f examples/zookeeper-operator/test/zkc-1.yaml")
        .wait_for_pod_status("zookeeper-cluster-0", RUNNING)
        .cmd("kubectl delete ZookeeperCluster zookeeper-cluster")
        .wait_for_pod_status("zookeeper-cluster-0", TERMINATED)
        .wait_for_pvc_status("data-zookeeper-cluster-0", TERMINATED)
        .cmd("kubectl apply -f examples/zookeeper-operator/test/zkc-1.yaml")
        .wait_for_pod_status("zookeeper-cluster-0", RUNNING)
        .wait(50),
        "scaledown-scaleup": new_built_in_workload()
        .cmd("kubectl apply -f examples/zookeeper-operator/test/zkc-2.yaml")
        .wait_for_pod_status("zookeeper-cluster-1", RUNNING)
        .wait(30)
        .cmd(
            'kubectl patch ZookeeperCluster zookeeper-cluster --type merge -p=\'{"spec":{"replicas":1}}\''
        )
        .wait_for_pod_status("zookeeper-cluster-1", TERMINATED)
        .wait_for_pvc_status("data-zookeeper-cluster-1", TERMINATED)
        .cmd(
            'kubectl patch ZookeeperCluster zookeeper-cluster --type merge -p=\'{"spec":{"replicas":2}}\''
        )
        .wait_for_pod_status("zookeeper-cluster-1", RUNNING)
        .wait(50),
    },
    "rabbitmq-operator": {
        "recreate": new_built_in_workload()
        .cmd("kubectl apply -f examples/rabbitmq-operator/test/rmqc-1.yaml")
        .wait_for_pod_status("rabbitmq-cluster-server-0", RUNNING)
        .cmd("kubectl delete RabbitmqCluster rabbitmq-cluster")
        .wait_for_pod_status("rabbitmq-cluster-server-0", TERMINATED)
        .cmd("kubectl apply -f examples/rabbitmq-operator/test/rmqc-1.yaml")
        .wait_for_pod_status("rabbitmq-cluster-server-0", RUNNING)
        .wait(50),
        "scaleup-scaledown": new_built_in_workload()
        .cmd("kubectl apply -f examples/rabbitmq-operator/test/rmqc-1.yaml")
        .wait_for_pod_status("rabbitmq-cluster-server-0", RUNNING)
        .cmd(
            'kubectl patch RabbitmqCluster rabbitmq-cluster --type merge -p=\'{"spec":{"replicas":3}}\''
        )
        .wait_for_pod_status("rabbitmq-cluster-server-2", RUNNING)
        .cmd(
            'kubectl patch RabbitmqCluster rabbitmq-cluster --type merge -p=\'{"spec":{"replicas":2}}\''
        )
        .wait(70),
        "resize-pvc": new_built_in_workload()
        .cmd("kubectl apply -f examples/rabbitmq-operator/test/rmqc-1.yaml")
        .wait_for_pod_status("rabbitmq-cluster-server-0", RUNNING)
        .cmd(
            'kubectl patch RabbitmqCluster rabbitmq-cluster --type merge -p=\'{"spec":{"persistence":{"storage":"15Gi"}}}\''
        )
        .wait_for_sts_storage_size("rabbitmq-cluster-server", "15Gi")
        .wait(80),
    },
    "mongodb-operator": {
        "recreate": new_built_in_workload()
        .cmd("kubectl apply -f examples/mongodb-operator/test/cr.yaml")
        .wait_for_pod_status("mongodb-cluster-rs0-2", RUNNING)
        .cmd("kubectl delete PerconaServerMongoDB mongodb-cluster")
        .wait_for_pod_status("mongodb-cluster-rs0-*", TERMINATED)
        .wait_for_pvc_status("mongod-data-mongodb-cluster-rs0-*", TERMINATED)
        .cmd("kubectl apply -f examples/mongodb-operator/test/cr.yaml")
        .wait_for_pod_status("mongodb-cluster-rs0-2", RUNNING)
        .wait(70),
        "disable-enable-shard": new_built_in_workload()
        .cmd("kubectl apply -f examples/mongodb-operator/test/cr-shard.yaml")
        .wait_for_pod_status("mongodb-cluster-rs0-2", RUNNING)
        .wait_for_pod_status("mongodb-cluster-cfg-2", RUNNING)
        .wait_for_pod_status("mongodb-cluster-mongos-*", RUNNING)
        .cmd(
            'kubectl patch PerconaServerMongoDB mongodb-cluster --type merge -p=\'{"spec":{"sharding":{"enabled":false}}}\''
        )
        .wait_for_pod_status("mongodb-cluster-cfg-2", TERMINATED)
        .wait_for_pod_status("mongodb-cluster-mongos-*", TERMINATED)
        .cmd(
            'kubectl patch PerconaServerMongoDB mongodb-cluster --type merge -p=\'{"spec":{"sharding":{"enabled":true}}}\''
        )
        .wait_for_pod_status("mongodb-cluster-cfg-2", RUNNING)
        .wait_for_pod_status("mongodb-cluster-mongos-*", RUNNING)
        .wait(70),
        "disable-enable-arbiter": new_built_in_workload()
        .cmd("kubectl apply -f examples/mongodb-operator/test/cr-arbiter.yaml")
        .wait_for_pod_status("mongodb-cluster-rs0-3", RUNNING, 150)
        .wait_for_pod_status("mongodb-cluster-rs0-arbiter-0", RUNNING)
        .cmd(
            'kubectl patch PerconaServerMongoDB mongodb-cluster --type=\'json\' -p=\'[{"op": "replace", "path": "/spec/replsets/0/arbiter/enabled", "value": false}]\''
        )
        .wait_for_pod_status("mongodb-cluster-rs0-arbiter-0", TERMINATED)
        .wait_for_pod_status("mongodb-cluster-rs0-4", RUNNING)
        .cmd(
            'kubectl patch PerconaServerMongoDB mongodb-cluster --type=\'json\' -p=\'[{"op": "replace", "path": "/spec/replsets/0/arbiter/enabled", "value": true}]\''
        )
        .wait_for_pod_status("mongodb-cluster-rs0-arbiter-0", RUNNING)
        .wait_for_pod_status("mongodb-cluster-rs0-4", TERMINATED)
        .wait(70),
        "run-cert-manager": new_built_in_workload()
        .cmd(
            "kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v0.15.1/cert-manager.yaml --validate=false"
        )
        .wait_for_pod_status(
            "cert-manager-webhook-*", RUNNING, namespace="cert-manager"
        )
        .cmd("kubectl apply -f examples/mongodb-operator/test/cr.yaml")
        .wait_for_pod_status("mongodb-cluster-rs0-2", RUNNING)
        .wait(70),
        "scaleup-scaledown": new_built_in_workload()
        .cmd("kubectl apply -f examples/mongodb-operator/test/cr.yaml")
        .wait_for_pod_status("mongodb-cluster-rs0-2", RUNNING)
        .cmd(
            'kubectl patch PerconaServerMongoDB mongodb-cluster --type=\'json\' -p=\'[{"op": "replace", "path": "/spec/replsets/0/size", "value": 5}]\''
        )
        .wait_for_pod_status("mongodb-cluster-rs0-4", RUNNING)
        .cmd(
            'kubectl patch PerconaServerMongoDB mongodb-cluster --type=\'json\' -p=\'[{"op": "replace", "path": "/spec/replsets/0/size", "value": 3}]\''
        )
        .wait_for_pod_status("mongodb-cluster-rs0-3", TERMINATED)
        .wait(70),
    },
    "xtradb-operator": {
        "recreate": new_built_in_workload()
        .cmd("kubectl apply -f examples/xtradb-operator/test/cr.yaml")
        .wait_for_pod_status("xtradb-cluster-pxc-2", RUNNING, 300)
        .cmd("kubectl delete perconaxtradbcluster xtradb-cluster")
        .wait_for_pod_status("xtradb-cluster-pxc-*", TERMINATED)
        .wait_for_pvc_status("datadir-xtradb-cluster-pxc-*", TERMINATED)
        .cmd("kubectl apply -f examples/xtradb-operator/test/cr.yaml")
        .wait_for_pod_status("xtradb-cluster-pxc-2", RUNNING, 300)
        .wait(70),
        "disable-enable-haproxy": new_built_in_workload()
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
        .wait_for_pod_status("xtradb-cluster-haproxy-0", RUNNING)
        .wait(70),
        "disable-enable-proxysql": new_built_in_workload()
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
        .wait_for_pod_status("xtradb-cluster-proxysql-0", RUNNING)
        .wait(70),
        "run-cert-manager": new_built_in_workload()
        .cmd(
            "kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v0.15.1/cert-manager.yaml --validate=false"
        )
        .wait_for_pod_status(
            "cert-manager-webhook-*", RUNNING, namespace="cert-manager"
        )
        .cmd("kubectl apply -f examples/xtradb-operator/test/cr.yaml")
        .wait_for_pod_status("xtradb-cluster-pxc-2", RUNNING, 250)
        .wait(70),
        "scaleup-scaledown": new_built_in_workload()
        .cmd("kubectl apply -f examples/xtradb-operator/test/cr.yaml")
        .wait_for_pod_status("xtradb-cluster-pxc-2", RUNNING, 300)
        .cmd('kubectl patch PerconaXtraDBCluster xtradb-cluster --type merge -p=\'{"spec":{"pxc":{"size":5}}}\'')
        .wait_for_pod_status("xtradb-cluster-pxc-3", RUNNING)
        .wait_for_pod_status("xtradb-cluster-pxc-4", RUNNING)
        .cmd('kubectl patch PerconaXtraDBCluster xtradb-cluster --type merge -p=\'{"spec":{"pxc":{"size":3}}}\'')
        .wait_for_pod_status("xtradb-cluster-pxc-3", TERMINATED, 300)
        .wait_for_pod_status("xtradb-cluster-pxc-4", TERMINATED, 300)
        .wait(70),
    },
    "yugabyte-operator": {
        "recreate": new_built_in_workload()
        .cmd("kubectl apply -f examples/yugabyte-operator/test/yb-1.yaml")
        .wait_for_pod_status("yb-master-2", RUNNING)
        .wait_for_pod_status("yb-tserver-2", RUNNING)
        .cmd("kubectl delete YBCluster example-ybcluster")
        .wait_for_pod_status("yb-master-0", TERMINATED)
        .wait_for_pod_status("yb-tserver-0", TERMINATED)
        .cmd("kubectl apply -f examples/yugabyte-operator/test/yb-1.yaml")
        .wait_for_pod_status("yb-master-2", RUNNING)
        .wait_for_pod_status("yb-tserver-2", RUNNING)
        .wait(70),
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
        .wait_for_secret_existence("yb-tserver-yugabyte-tls-cert", EXIST)
        .wait(70),
        "disable-enable-tuiport": new_built_in_workload()
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
        .wait_for_service_existence("yb-tserver-ui", EXIST)
        .wait(70),
        "scaleup-scaledown-tserver": new_built_in_workload()
        .cmd("kubectl apply -f examples/yugabyte-operator/test/yb-1.yaml")
        .wait_for_pod_status("yb-master-2", RUNNING)
        .wait_for_pod_status("yb-tserver-2", RUNNING)
        .cmd(
            'kubectl patch YBCluster example-ybcluster --type merge -p=\'{"spec":{"tserver":{"replicas":4},"replicationFactor":4}}\''
        )
        .wait_for_pod_status("yb-tserver-3", RUNNING, 20)
        .cmd(
            'kubectl patch YBCluster example-ybcluster --type merge -p=\'{"spec":{"tserver":{"replicas":3},"replicationFactor":4}}\''
        )
        .wait(70),
    },
    "nifikop-operator": {
        "change-config": new_built_in_workload()
        .cmd("kubectl apply -f examples/nifikop-operator/test/nc-1.yaml")
        .wait_for_pod_status("simplenifi-1-*", RUNNING, 220)
        .wait_for_cr_condition(
            "nificluster",
            "simplenifi",
            [["metadata/finalizers", ["nificlusters.nifi.orange.com/finalizer"]]],
        )  # then wait for finializer to be present
        .cmd("kubectl apply -f examples/nifikop-operator/test/nc-config.yaml")
        .wait_for_cr_condition(
            "nificluster",
            "simplenifi",
            [["metadata/finalizers", ["nificlusters.nifi.orange.com/finalizer"]]],
        )  # then wait for finializer to be present
        .wait(30)
        .wait_for_pod_status("simplenifi-1-*", RUNNING, 120)
        .wait_for_cr_condition(
            "nificluster",
            "simplenifi",
            [["metadata/finalizers", ["nificlusters.nifi.orange.com/finalizer"]]],
        )  # then wait for finializer to be present
        .wait(60),
        "recreate": new_built_in_workload()
        .cmd("kubectl apply -f examples/nifikop-operator/test/nc-1.yaml")
        .wait_for_pod_status("simplenifi-1-*", RUNNING)
        .wait_for_cr_condition(
            "nificluster",
            "simplenifi",
            [["metadata/finalizers", ["nificlusters.nifi.orange.com/finalizer"]]],
        )  # then wait for finializer to be present
        .cmd("kubectl delete nificluster simplenifi")
        .wait_for_pod_status("simplenifi-1-*", TERMINATED)
        .cmd("kubectl apply -f examples/nifikop-operator/test/nc-1.yaml")
        .wait_for_pod_status("simplenifi-1-*", RUNNING)
        .wait_for_cr_condition(
            "nificluster",
            "simplenifi",
            [["metadata/finalizers", ["nificlusters.nifi.orange.com/finalizer"]]],
        )  # then wait for finializer to be present
        .wait(60),
        "scaledown-scaleup": new_built_in_workload()
        .cmd("kubectl apply -f examples/nifikop-operator/test/nc-2.yaml")
        .wait_for_pod_status("simplenifi-1-*", RUNNING)
        .wait_for_pod_status("simplenifi-2-*", RUNNING)
        # then wait for finializer to be present
        .wait_for_cr_condition(
            "nificluster",
            "simplenifi",
            [["metadata/finalizers", ["nificlusters.nifi.orange.com/finalizer"]]],
        )
        .cmd(
            'kubectl patch nificluster simplenifi --type=\'json\' -p=\'[{"op": "remove", "path": "/spec/nodes/1"}]\''
        )
        .wait_for_pod_status("simplenifi-2-*", TERMINATED)
        .cmd(
            'kubectl patch nificluster simplenifi --type=\'json\' -p=\'[{"op": "add", "path": "/spec/nodes/1", "value": {"id": 2, "nodeConfigGroup": "default_group"}}]\''
        )
        .wait_for_pod_status("simplenifi-2-*", RUNNING)
        # then wait for finializer to be present
        .wait_for_cr_condition(
            "nificluster",
            "simplenifi",
            [["metadata/finalizers", ["nificlusters.nifi.orange.com/finalizer"]]],
        ).wait(60),
    },
}
