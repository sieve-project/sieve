import os


class Suite:
    def __init__(self, workload, config, mode, double_sides=False):
        self.workload = workload
        self.config = config
        self.mode = mode
        self.double_sides = double_sides


docker_repo = "xudongs"

testing_modes = ["time-travel", "sparse-read"]

github_link = {
    "cassandra-operator": "git@github.com:instaclustr/cassandra-operator.git",
    "zookeeper-operator": "git@github.com:pravega/zookeeper-operator.git",
    "rabbitmq-operator": "git@github.com:rabbitmq/cluster-operator.git",
    "kafka-operator": "git@github.com:banzaicloud/kafka-operator.git",
}

test_suites = {
    "cassandra-operator": {
        "test1": Suite(
            "scaleDownCassandraDataCenter.sh", "test-cassandra-operator/test/sparse-read-1.yaml", "sparse-read"),
        "test2": Suite(
            "recreateCassandraDataCenter.sh", "test-cassandra-operator/test/time-travel-1.yaml", "time-travel"),
        # "test3": Suite(
        #     "recreateCassandraDataCenter.sh", "test-cassandra-operator/test/bug3.yaml", "time-travel"),
        "test4": Suite(
            "scaleDownUpCassandraDataCenter.sh", "test-cassandra-operator/test/time-travel-2.yaml", "time-travel"),
    },
    "zookeeper-operator": {
        "test1": Suite(
            "recreateZookeeperCluster.sh", "test-zookeeper-operator/test/time-travel-1.yaml", "time-travel"),
        "test2": Suite(
            "scaleDownUpZookeeperCluster.sh", "test-zookeeper-operator/test/time-travel-2.yaml", "time-travel"),
    },
    "rabbitmq-operator": {
        "test1": Suite(
            "recreateRabbitmqCluster.sh", "test-rabbitmq-operator/test/time-travel-1.yaml", "time-travel"),
        "test2": Suite(
            "resizePVCRabbitmqCluster.sh", "test-rabbitmq-operator/test/time-travel-2.yaml", "time-travel", True),
    },
    "kafka-operator": {
        "test1": Suite(
            "todo.sh", "test-kafka-operator/test/time-travel-1.yaml", "time-travel"),
    }
}

CRDs = {
    "cassandra-operator": ["cassandradatacenter", "cassandracluster", "cassandrabackup"],
    "zookeeper-operator": ["zookeepercluster"],
    "rabbitmq-operator": ["rabbitmqcluster"],
    "kafka-operator": ["kafkacluster", "kafkatopic", "kafkauser"],
}

command = {
    "cassandra-operator": "/cassandra-operator",
    "zookeeper-operator": "/usr/local/bin/zookeeper-operator",
    "rabbitmq-operator": "/manager",
    "kafka-operator": "/manager",
}

controller_runtime_version = {
    "cassandra-operator": "@v0.4.0",
    "zookeeper-operator": "@v0.5.2",
    "rabbitmq-operator": "@v0.8.3",
    "kafka-operator": "@v0.6.5"
}

client_go_version = {
    "cassandra-operator": "@v0.0.0-20190918160344-1fbdaa4c8d90",
    "zookeeper-operator": "@v0.17.2",
    "rabbitmq-operator": "@v0.20.2",
    "kafka-operator": "@v0.18.9"
}

sha = {
    "cassandra-operator": "fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd",
    "zookeeper-operator": "cda03d2f270bdfb51372192766123904f6d88278",
    "rabbitmq-operator": "4f13b9a942ad34fece0171d2174aa0264b10e947",
    "kafka-operator": "60caff461c5372e5fdb8e117f83fa1b6b4a9e53b",
}

docker_file = {
    "cassandra-operator": "docker/cassandra-operator/Dockerfile",
    "zookeeper-operator": "Dockerfile",
    "rabbitmq-operator": "Dockerfile",
    "kafka-operator": "Dockerfile",
}

learning_configs = {
    "cassandra-operator": "test-cassandra-operator/test/learn.yaml",
    "zookeeper-operator": "test-zookeeper-operator/test/learn.yaml",
    "rabbitmq-operator": "test-rabbitmq-operator/test/learn.yaml",
    "kafka-operator": "test-kafka-operator/test/learn.yaml",
}


def replace_docker_repo(path, dr, dt):
    fin = open(path)
    data = fin.read()
    data = data.replace("${SONAR-DR}", dr)
    data = data.replace("${SONAR-DT}", dt)
    fin.close()
    tokens = path.rsplit('.', 1)
    new_path = tokens[0] + "-" + dr + '.' + tokens[1]
    fin = open(new_path, "w")
    fin.write(data)
    fin.close()
    return new_path


def cassandra_operator_deploy(dr, dt):
    new_path = replace_docker_repo(
        "test-cassandra-operator/deploy/bundle.yaml", dr, dt)
    os.system("kubectl apply -f test-cassandra-operator/deploy/crds.yaml")
    os.system(
        "kubectl apply -f %s" % new_path)
    os.system("rm %s" % new_path)


def zookeeper_operator_deploy(dr, dt):
    new_path = replace_docker_repo(
        "test-zookeeper-operator/deploy/default_ns/operator.yaml", dr, dt)
    os.system("kubectl create -f test-zookeeper-operator/deploy/crds")
    os.system(
        "kubectl create -f test-zookeeper-operator/deploy/default_ns/rbac.yaml")
    os.system(
        "kubectl create -f %s" % new_path)
    os.system("rm %s" % new_path)


def rabbitmq_operator_deploy(dr, dt):
    new_path = replace_docker_repo(
        "test-rabbitmq-operator/deploy/cluster-operator.yaml", dr, dt)
    os.system("kubectl apply -f %s" % new_path)
    os.system("rm %s" % new_path)


deploy = {
    "cassandra-operator": cassandra_operator_deploy,
    "zookeeper-operator": zookeeper_operator_deploy,
    "rabbitmq-operator": rabbitmq_operator_deploy,
}
