import os


class Suite:
    def __init__(self, workload, config):
        self.workload = workload
        self.config = config


test_suites = {
    "cassandra-operator": {
        "test1": Suite(
            "scaleDownCassandraDataCenter.sh", "test-cassandra-operator/config/bug1.yaml"),
        "test2": Suite(
            "recreateCassandraDataCenter.sh", "test-cassandra-operator/config/bug2.yaml"),
        "test3": Suite(
            "recreateCassandraDataCenter.sh", "test-cassandra-operator/config/bug3.yaml"),
        "test4": Suite(
            "scaleDownUpCassandraDataCenter.sh", "test-cassandra-operator/config/bug4.yaml")
    },
    "zookeeper-operator": {
        "test1": Suite(
            "recreateZookeeperCluster.sh", "test-zookeeper-operator/config/bug1.yaml"),
        "test2": Suite(
            "scaleDownUpZookeeperCluster.sh", "test-zookeeper-operator/config/bug2.yaml")
    }
}

CRDs = {
    "cassandra-operator": ["cassandradatacenters", "cassandraclusters", "cassandrabackups"],
    "zookeeper-operator": ["zookeeperclusters"]
}


def cassandraOperatorBootstrap():
    os.system("kubectl apply -f test-cassandra-operator/config/crds.yaml")
    os.system("kubectl apply -f test-cassandra-operator/config/bundle.yaml")


def zookeeperOperatorBootstrap():
    os.system("kubectl create -f test-zookeeper-operator/config/deploy/crds")
    os.system(
        "kubectl create -f test-zookeeper-operator/config/deploy/default_ns/rbac.yaml")
    os.system(
        "kubectl create -f test-zookeeper-operator/config/deploy/default_ns/operator.yaml")


bootstrap = {
    "cassandra-operator": cassandraOperatorBootstrap,
    "zookeeper-operator": zookeeperOperatorBootstrap
}
