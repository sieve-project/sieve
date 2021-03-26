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
