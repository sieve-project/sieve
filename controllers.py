import os
import kubernetes
import time


class Suite:
    def __init__(self, workload, config, mode, double_sides=False, cluster_config="kind-ha.yaml"):
        self.workload = workload
        self.config = config
        self.mode = mode
        self.double_sides = double_sides
        self.cluster_config = cluster_config


docker_repo = "xudongs"

testing_modes = ["time-travel", "sparse-read"]

github_link = {
    "cassandra-operator": "git@github.com:instaclustr/cassandra-operator.git",
    "zookeeper-operator": "git@github.com:pravega/zookeeper-operator.git",
    "rabbitmq-operator": "git@github.com:rabbitmq/cluster-operator.git",
    "mongodb-operator": "git@github.com:percona/percona-server-mongodb-operator.git",
    "cass-operator": "git@github.com:datastax/cass-operator.git",
    "casskop-operator": "git@github.com:Orange-OpenSource/casskop.git",
    "xtradb-operator": "git@github.com:percona/percona-xtradb-cluster-operator.git",
}

app_dir = {
    "cassandra-operator": "app/cassandra-operator",
    "zookeeper-operator": "app/zookeeper-operator",
    "rabbitmq-operator": "app/rabbitmq-operator",
    "mongodb-operator": "app/mongodb-operator",
    "cass-operator": "app/cass-operator",
    "casskop-operator": "app/casskop-operator",
    "xtradb-operator": "app/xtradb-operator",
}

test_dir = {
    "cassandra-operator": "test-cassandra-operator/test",
    "zookeeper-operator": "test-zookeeper-operator/test",
    "rabbitmq-operator": "test-rabbitmq-operator/test",
    "mongodb-operator": "test-mongodb-operator/test",
    "cass-operator": "test-cass-operator/test",
    "casskop-operator": "test-casskop-operator/test",
    "xtradb-operator": "test-xtradb-operator/test",
}

test_suites = {
    "cassandra-operator": {
        "test1": Suite(
            "scaleDownCassandraDataCenter.sh", "test-cassandra-operator/test/sparse-read-1.yaml", "sparse-read"),
        "test2": Suite(
            "recreateCassandraDataCenter.sh", "test-cassandra-operator/test/time-travel-1.yaml", "time-travel"),
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
            "resizePVCRabbitmqCluster.sh", "test-rabbitmq-operator/test/time-travel-2.yaml", "time-travel", double_sides=True),
    },
    "mongodb-operator": {
        "test1": Suite(
            "recreateMongodbCluster.sh", "test-mongodb-operator/test/time-travel-1.yaml", "time-travel", cluster_config="kind-ha-4w.yaml"),
        "test2": Suite(
            "disableEnableShard.sh", "test-mongodb-operator/test/time-travel-2.yaml", "time-travel", cluster_config="kind-ha-4w.yaml"),
        "test3": Suite(
            "disableEnableArbiter.sh", "test-mongodb-operator/test/time-travel-3.yaml", "time-travel", cluster_config="kind-ha-4w.yaml"),
    },
    "cass-operator": {
        "test1": Suite(
            "recreateCassandraDataCenter.sh", "test-cass-operator/test/time-travel-1.yaml", "time-travel"),
    },
    "casskop-operator": {
        "test1": Suite(
            "recreateCassandraCluster.sh", "test-casskop-operator/test/time-travel-1.yaml", "time-travel"),
    },
    "xtradb-operator": {
        "test1": Suite(
            "recreateXtradbCluster.sh", "test-xtradb-operator/test/time-travel-1.yaml", "time-travel", cluster_config="kind-ha-4w.yaml"),
        "test2": Suite(
            "disableEnableHaproxy.sh", "test-xtradb-operator/test/time-travel-2.yaml", "time-travel", cluster_config="kind-ha-4w.yaml"),
    },
}

CRDs = {
    "cassandra-operator": ["cassandradatacenter", "cassandracluster", "cassandrabackup"],
    "zookeeper-operator": ["zookeepercluster"],
    "rabbitmq-operator": ["rabbitmqcluster"],
    "mongodb-operator": ["perconaservermongodb", "perconaservermongodbbackup", "perconaservermongodbrestore"],
    "cass-operator": ["cassandradatacenter"],
    "casskop-operator": ["cassandracluster", "cassandrarestore", "cassandrabackup"],
    "xtradb-operator": ["perconaxtradbcluster", "perconaxtradbclusterbackup", "perconaxtradbclusterrestore", "perconaxtradbbackup"],
}

command = {
    "cassandra-operator": "/cassandra-operator",
    "zookeeper-operator": "/usr/local/bin/zookeeper-operator",
    "rabbitmq-operator": "/manager",
    "mongodb-operator": "percona-server-mongodb-operator",
    "cass-operator": "/bin/operator",
    "casskop-operator": "/usr/local/bin/casskop",
    "xtradb-operator": "percona-xtradb-cluster-operator",
}

controller_runtime_version = {
    "cassandra-operator": "v0.4.0",
    "zookeeper-operator": "v0.5.2",
    "rabbitmq-operator": "v0.8.3",
    "mongodb-operator": "v0.5.2",
    "cass-operator": "v0.5.2",
    "casskop-operator": "v0.6.0",
    "xtradb-operator": "v0.6.2",
}

client_go_version = {
    "cassandra-operator": "v0.0.0-20190918160344-1fbdaa4c8d90",
    "zookeeper-operator": "v0.17.2",
    "rabbitmq-operator": "v0.20.2",
    "mongodb-operator": "v0.17.2",
    "cass-operator": "v0.17.4",
    "casskop-operator": "v0.18.2",
    "xtradb-operator": "v0.18.6",
}

sha = {
    "cassandra-operator": "fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd",
    "zookeeper-operator": "cda03d2f270bdfb51372192766123904f6d88278",
    "rabbitmq-operator": "4f13b9a942ad34fece0171d2174aa0264b10e947",
    "mongodb-operator": "c12b69e2c41efc67336a890039394250420f60bb",
    "cass-operator": "dbd4f7a10533bb2298aed0d40ea20bfd8c133da2",
    "casskop-operator": "f87c8e05c1a2896732fc5f3a174f1eb99e936907",
    "xtradb-operator": "29092c9b145af6eaf5cbff534287483bec4167b6",
}

docker_file = {
    "cassandra-operator": "docker/cassandra-operator/Dockerfile",
    "zookeeper-operator": "Dockerfile",
    "rabbitmq-operator": "Dockerfile",
    "mongodb-operator": "build/Dockerfile",
    "cass-operator": "operator/docker/base/Dockerfile",
    "casskop-operator": "build/Dockerfile",
    "xtradb-operator": "build/Dockerfile",
}

learning_configs = {
    "cassandra-operator": "test-cassandra-operator/test/learn.yaml",
    "zookeeper-operator": "test-zookeeper-operator/test/learn.yaml",
    "rabbitmq-operator": "test-rabbitmq-operator/test/learn.yaml",
    "mongodb-operator": "test-mongodb-operator/test/learn.yaml",
    "cass-operator": "test-cass-operator/test/learn.yaml",
    "casskop-operator": "test-casskop-operator/test/learn.yaml",
    "xtradb-operator": "test-xtradb-operator/test/learn.yaml",
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


def mongodb_operator_deploy(dr, dt):
    new_path = replace_docker_repo(
        "test-mongodb-operator/deploy/bundle.yaml", dr, dt)
    os.system("kubectl apply -f %s" % new_path)
    os.system("rm %s" % new_path)

def cass_operator_deploy(dr, dt):
    new_path = replace_docker_repo(
        "test-cass-operator/deploy/controller-manifest.yaml", dr, dt)
    os.system("kubectl apply -f %s" % new_path)
    os.system("kubectl apply -f test-cass-operator/deploy/storageClass.yaml")
    os.system("rm %s" % new_path)


def casskop_operator_deploy(dr, dt):
    # Using helm
    new_path = replace_docker_repo(
        "test-casskop-operator/deploy/values.yaml", dr, dt)
    os.system("helm install -f %s casskop-operator test-casskop-operator/deploy"%(new_path))

def xtradb_operator_deploy(dr, dt):
    new_path = replace_docker_repo(
        "test-xtradb-operator/deploy/bundle.yaml", dr, dt)
    os.system("kubectl apply -f %s" % new_path)
    os.system("rm %s" % new_path)

deploy = {
    "cassandra-operator": cassandra_operator_deploy,
    "zookeeper-operator": zookeeper_operator_deploy,
    "rabbitmq-operator": rabbitmq_operator_deploy,
    "mongodb-operator": mongodb_operator_deploy,
    "cass-operator": cass_operator_deploy,
    "casskop-operator": casskop_operator_deploy,
    "xtradb-operator": xtradb_operator_deploy,
}
