import os


class Suite:
    def __init__(self, workload, config):
        self.workload = workload
        self.config = config


docker_repo = "xudongs"

github_link = {
    "cassandra-operator": "git@github.com:instaclustr/cassandra-operator.git",
    "zookeeper-operator": "git@github.com:pravega/zookeeper-operator.git",
}

test_suites = {
    "cassandra-operator": {
        "test1": Suite(
            "scaleDownCassandraDataCenter.sh", "test-cassandra-operator/config/bug1.yaml"),
        "test2": Suite(
            "recreateCassandraDataCenter.sh", "test-cassandra-operator/config/bug2.yaml"),
        "test3": Suite(
            "recreateCassandraDataCenter.sh", "test-cassandra-operator/config/bug3.yaml"),
        "test4": Suite(
            "scaleDownUpCassandraDataCenter.sh", "test-cassandra-operator/config/bug4.yaml"),
    },
    "zookeeper-operator": {
        "test1": Suite(
            "recreateZookeeperCluster.sh", "test-zookeeper-operator/config/bug1.yaml"),
        "test2": Suite(
            "scaleDownUpZookeeperCluster.sh", "test-zookeeper-operator/config/bug2.yaml"),
    },
}

CRDs = {
    "cassandra-operator": ["cassandradatacenters", "cassandraclusters", "cassandrabackups"],
    "zookeeper-operator": ["zookeeperclusters"],
}

command = {
    "cassandra-operator": "/cassandra-operator",
    "zookeeper-operator": "/usr/local/bin/zookeeper-operator",
}

controller_runtime_version = {
    "cassandra-operator": "@v0.4.0",
    "zookeeper-operator": "@v0.5.2",
}

client_go_version = {
    "cassandra-operator": "@v0.0.0-20190918160344-1fbdaa4c8d90",
    "zookeeper-operator": "@v0.17.2",
}

sha = {
    "cassandra-operator": "fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd",
    "zookeeper-operator": "cda03d2f270bdfb51372192766123904f6d88278",
}

docker_file = {
    "cassandra-operator": "docker/cassandra-operator/Dockerfile",
    "zookeeper-operator": "Dockerfile",
}


def replaceDockerRepo(path, dr):
    fin = open(path)
    data = fin.read()
    data = data.replace("${SONAR-DR}", dr)
    fin.close()
    tokens = path.rsplit('.', 1)
    new_path = tokens[0] + "-" + dr + '.' + tokens[1]
    fin = open(new_path, "w")
    fin.write(data)
    fin.close()
    return new_path


def cassandraOperatorBootstrap(dr):
    new_path = replaceDockerRepo(
        "test-cassandra-operator/config/bundle.yaml", dr)
    os.system("kubectl apply -f test-cassandra-operator/config/crds.yaml")
    os.system(
        "kubectl apply -f %s" % new_path)
    os.system("rm %s" % new_path)


def zookeeperOperatorBootstrap(dr):
    new_path = replaceDockerRepo(
        "test-zookeeper-operator/config/deploy/default_ns/operator.yaml", dr)
    os.system("kubectl create -f test-zookeeper-operator/config/deploy/crds")
    os.system(
        "kubectl create -f test-zookeeper-operator/config/deploy/default_ns/rbac.yaml")
    os.system(
        "kubectl create -f %s" % new_path)
    os.system("rm %s" % new_path)


bootstrap = {
    "cassandra-operator": cassandraOperatorBootstrap,
    "zookeeper-operator": zookeeperOperatorBootstrap,
}
