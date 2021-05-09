import os
import kubernetes
import time
import re
import workloads
import test_framework


class Suite:
    def __init__(self, workload, config, mode, two_sided=False, num_workers=2):
        self.workload = workload
        self.config = config
        self.mode = mode
        self.two_sided = two_sided
        self.num_workers = num_workers


docker_repo = "xudongs"
front_runner = "kind-control-plane"
straggler = "kind-control-plane3"

testing_modes = ["time-travel", "sparse-read"]

github_link = {
    "cassandra-operator": "https://github.com/instaclustr/cassandra-operator.git",
    "zookeeper-operator": "https://github.com/pravega/zookeeper-operator.git",
    "rabbitmq-operator": "https://github.com/rabbitmq/cluster-operator.git",
    "mongodb-operator": "https://github.com/percona/percona-server-mongodb-operator.git",
    "cass-operator": "https://github.com/datastax/cass-operator.git",
    "casskop-operator": "https://github.com/Orange-OpenSource/casskop.git",
}

app_dir = {
    "cassandra-operator": "app/cassandra-operator",
    "zookeeper-operator": "app/zookeeper-operator",
    "rabbitmq-operator": "app/rabbitmq-operator",
    "mongodb-operator": "app/mongodb-operator",
    "cass-operator": "app/cass-operator",
    "casskop-operator": "app/casskop-operator",
}

test_dir = {
    "cassandra-operator": "test-cassandra-operator",
    "zookeeper-operator": "test-zookeeper-operator",
    "rabbitmq-operator": "test-rabbitmq-operator",
    "mongodb-operator": "test-mongodb-operator",
    "cass-operator": "test-cass-operator",
    "casskop-operator": "test-casskop-operator",
}

test_dir_test = {
    "cassandra-operator": os.path.join(test_dir["cassandra-operator"], "test"),
    "zookeeper-operator": os.path.join(test_dir["zookeeper-operator"], "test"),
    "rabbitmq-operator": os.path.join(test_dir["rabbitmq-operator"], "test"),
    "mongodb-operator": os.path.join(test_dir["mongodb-operator"], "test"),
    "cass-operator": os.path.join(test_dir["cass-operator"], "test"),
    "casskop-operator": os.path.join(test_dir["casskop-operator"], "test"),
}

test_suites = {
    "cassandra-operator": {
        "scaledown": Suite(
            test_framework.ExtendedWorkload(test_dir_test["cassandra-operator"], "./scaleDownCassandraDataCenter.sh", True), "test-cassandra-operator/test/sparse-read-1.yaml", "sparse-read"),
        "recreate": Suite(
            workloads.workloads["cassandra-operator"]["recreate"], "test-cassandra-operator/test/time-travel-1.yaml", "time-travel"),
        "scaledown-scaleup": Suite(
            workloads.workloads["cassandra-operator"]["scaledown-scaleup"], "test-cassandra-operator/test/time-travel-2.yaml", "time-travel"),
    },
    "zookeeper-operator": {
        "recreate": Suite(
            workloads.workloads["zookeeper-operator"]["recreate"], "test-zookeeper-operator/test/time-travel-1.yaml", "time-travel"),
        "scaledown-scaleup": Suite(
            workloads.workloads["zookeeper-operator"]["scaledown-scaleup"], "test-zookeeper-operator/test/time-travel-2.yaml", "time-travel"),
    },
    "rabbitmq-operator": {
        "recreate": Suite(
            workloads.workloads["rabbitmq-operator"]["recreate"], "test-rabbitmq-operator/test/time-travel-1.yaml", "time-travel"),
        "resize-pvc": Suite(
            workloads.workloads["rabbitmq-operator"]["resize-pvc"], "test-rabbitmq-operator/test/time-travel-2.yaml", "time-travel", two_sided=True),
    },
    "mongodb-operator": {
        "recreate": Suite(
            workloads.workloads["mongodb-operator"]["recreate"], "test-mongodb-operator/test/time-travel-1.yaml", "time-travel", num_workers=3),
        "disable-enable-shard": Suite(
            workloads.workloads["mongodb-operator"]["disable-enable-shard"], "test-mongodb-operator/test/time-travel-2.yaml", "time-travel", num_workers=3),
        "disable-enable-arbiter": Suite(
            workloads.workloads["mongodb-operator"]["disable-enable-arbiter"], "test-mongodb-operator/test/time-travel-3.yaml", "time-travel", num_workers=5),
        "enable-shard": Suite(
            workloads.workloads["mongodb-operator"]["enable-shard"], "config/none.yaml", "time-travel", num_workers=3),
    },
    "cass-operator": {
        "recreate": Suite(
            test_framework.ExtendedWorkload(test_dir_test["cass-operator"], "./recreateCassandraDataCenter.sh", True), "test-cass-operator/test/time-travel-1.yaml", "time-travel"),
    },
    "casskop-operator": {
        "recreate": Suite(
            test_framework.ExtendedWorkload(test_dir_test["casskop-operator"], "./recreateCassandraCluster.sh", True), "test-casskop-operator/test/time-travel-1.yaml", "time-travel"),
    },
}

CRDs = {
    "cassandra-operator": ["cassandradatacenter", "cassandracluster", "cassandrabackup"],
    "zookeeper-operator": ["zookeepercluster"],
    "rabbitmq-operator": ["rabbitmqcluster"],
    "mongodb-operator": ["perconaservermongodb", "perconaservermongodbbackup", "perconaservermongodbrestore"],
    "cass-operator": ["cassandradatacenter"],
    "casskop-operator": ["cassandracluster", "cassandrarestore", "cassandrabackup"],
}

deployment_name = {
    "cassandra-operator": "cassandra-operator",
    "zookeeper-operator": "zookeeper-operator",
    "rabbitmq-operator": "rabbitmq-operator",
    "mongodb-operator": "percona-server-mongodb-operator",
    "casskop-operator": "casskop-operator",
}

operator_pod_label = {
    "cassandra-operator": "cassandra-operator",
    "zookeeper-operator": "zookeeper-operator",
    "rabbitmq-operator": "rabbitmq-operator",
    "mongodb-operator": "mongodb-operator",
    "casskop-operator": "casskop-operator",
}

# command = {
#     "cassandra-operator": "/cassandra-operator",
#     "zookeeper-operator": "/usr/local/bin/zookeeper-operator",
#     "rabbitmq-operator": "/manager",
#     "mongodb-operator": "percona-server-mongodb-operator",
#     "cass-operator": "/bin/operator",
#     "casskop-operator": "/usr/local/bin/casskop"
# }

controller_runtime_version = {
    "cassandra-operator": "v0.4.0",
    "zookeeper-operator": "v0.5.2",
    "rabbitmq-operator": "v0.8.3",
    "mongodb-operator": "v0.5.2",
    "cass-operator": "v0.5.2",
    "casskop-operator": "v0.6.0",
}

client_go_version = {
    "cassandra-operator": "v0.0.0-20190918160344-1fbdaa4c8d90",
    "zookeeper-operator": "v0.17.2",
    "rabbitmq-operator": "v0.20.2",
    "mongodb-operator": "v0.17.2",
    "cass-operator": "v0.17.4",
    "casskop-operator": "v0.18.2",
}

sha = {
    "cassandra-operator": "fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd",
    "zookeeper-operator": "cda03d2f270bdfb51372192766123904f6d88278",
    "rabbitmq-operator": "4f13b9a942ad34fece0171d2174aa0264b10e947",
    "mongodb-operator": "c12b69e2c41efc67336a890039394250420f60bb",
    "cass-operator": "dbd4f7a10533bb2298aed0d40ea20bfd8c133da2",
    "casskop-operator": "f87c8e05c1a2896732fc5f3a174f1eb99e936907",
}

docker_file = {
    "cassandra-operator": "docker/cassandra-operator/Dockerfile",
    "zookeeper-operator": "Dockerfile",
    "rabbitmq-operator": "Dockerfile",
    "mongodb-operator": "build/Dockerfile",
    "cass-operator": "operator/docker/base/Dockerfile",
    "casskop-operator": "build/Dockerfile",
}

# learning_configs = {
#     "cassandra-operator": "test-cassandra-operator/test/learn.yaml",
#     "zookeeper-operator": "test-zookeeper-operator/test/learn.yaml",
#     "rabbitmq-operator": "test-rabbitmq-operator/test/learn.yaml",
#     "mongodb-operator": "test-mongodb-operator/test/learn.yaml",
#     "cass-operator": "test-cass-operator/test/learn.yaml",
#     "casskop-operator": "test-casskop-operator/test/learn.yaml",
# }


def make_safe_filename(filename):
    return re.sub(r'[^\w\d-]', '_', filename)


def replace_docker_repo(path, dr, dt):
    fin = open(path)
    data = fin.read()
    data = data.replace("${SONAR-DR}", dr)
    data = data.replace("${SONAR-DT}", dt)
    fin.close()
    tokens = path.rsplit('.', 1)
    new_path = tokens[0] + "-" + make_safe_filename(dr) + '.' + tokens[1]
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
    os.system(
        "helm install -f %s casskop-operator test-casskop-operator/deploy" % (new_path))


deploy = {
    "cassandra-operator": cassandra_operator_deploy,
    "zookeeper-operator": zookeeper_operator_deploy,
    "rabbitmq-operator": rabbitmq_operator_deploy,
    "mongodb-operator": mongodb_operator_deploy,
    "cass-operator": cass_operator_deploy,
    "casskop-operator": casskop_operator_deploy,
}
