import os
import re
import workloads
from common import sieve_modes, Suite

github_link = {
    "cassandra-operator": "https://github.com/instaclustr/cassandra-operator.git",
    "zookeeper-operator": "https://github.com/pravega/zookeeper-operator.git",
    "rabbitmq-operator": "https://github.com/rabbitmq/cluster-operator.git",
    "mongodb-operator": "https://github.com/percona/percona-server-mongodb-operator.git",
    "cass-operator": "https://github.com/datastax/cass-operator.git",
    "casskop-operator": "https://github.com/Orange-OpenSource/casskop.git",
    "xtradb-operator": "https://github.com/percona/percona-xtradb-cluster-operator.git",
    "yugabyte-operator": "https://github.com/yugabyte/yugabyte-operator.git",
    "nifikop-operator": "https://github.com/Orange-OpenSource/nifikop.git",
}

app_dir = {
    "cassandra-operator": "app/cassandra-operator",
    "zookeeper-operator": "app/zookeeper-operator",
    "rabbitmq-operator": "app/rabbitmq-operator",
    "mongodb-operator": "app/mongodb-operator",
    "cass-operator": "app/cass-operator",
    "casskop-operator": "app/casskop-operator",
    "xtradb-operator": "app/xtradb-operator",
    "yugabyte-operator": "app/yugabyte-operator",
    "nifikop-operator": "app/nifikop-operator",
}

test_dir = {
    "cassandra-operator": "test-cassandra-operator",
    "zookeeper-operator": "test-zookeeper-operator",
    "rabbitmq-operator": "test-rabbitmq-operator",
    "mongodb-operator": "test-mongodb-operator",
    "cass-operator": "test-cass-operator",
    "casskop-operator": "test-casskop-operator",
    "xtradb-operator": "test-xtradb-operator",
    "yugabyte-operator": "test-yugabyte-operator",
    "nifikop-operator": "test-nifikop-operator",
}

test_dir_test = {
    "cassandra-operator": os.path.join(test_dir["cassandra-operator"], "test"),
    "zookeeper-operator": os.path.join(test_dir["zookeeper-operator"], "test"),
    "rabbitmq-operator": os.path.join(test_dir["rabbitmq-operator"], "test"),
    "mongodb-operator": os.path.join(test_dir["mongodb-operator"], "test"),
    "cass-operator": os.path.join(test_dir["cass-operator"], "test"),
    "casskop-operator": os.path.join(test_dir["casskop-operator"], "test"),
    "xtradb-operator": os.path.join(test_dir["xtradb-operator"], "test"),
    "yugabyte-operator": os.path.join(test_dir["yugabyte-operator"], "test"),
    "nifikop-operator": os.path.join(test_dir["nifikop-operator"], "test"),
}

test_suites = {
    "cassandra-operator": {
        "scaledown": Suite(
            workloads.workloads["cassandra-operator"]["scaledown"], "test-cassandra-operator/test/obs-gap-1.yaml", sieve_modes.OBS_GAP),
        "recreate": Suite(
            workloads.workloads["cassandra-operator"]["recreate"], "test-cassandra-operator/test/time-travel-1.yaml", sieve_modes.TIME_TRAVEL),
        "scaledown-scaleup": Suite(
            workloads.workloads["cassandra-operator"]["scaledown-scaleup"], "test-cassandra-operator/test/time-travel-2.yaml", sieve_modes.TIME_TRAVEL),
    },
    "zookeeper-operator": {
        "recreate": Suite(
            workloads.workloads["zookeeper-operator"]["recreate"], "test-zookeeper-operator/test/time-travel-1.yaml", sieve_modes.TIME_TRAVEL),
        "scaledown-scaleup": Suite(
            workloads.workloads["zookeeper-operator"]["scaledown-scaleup"], "test-zookeeper-operator/test/time-travel-2.yaml", sieve_modes.TIME_TRAVEL),
        "scaledown-scaleup-obs": Suite(
            workloads.workloads["zookeeper-operator"]["scaledown-scaleup-obs"], "test-zookeeper-operator/test/obs-gap-1.yaml", sieve_modes.OBS_GAP),
    },
    "rabbitmq-operator": {
        "recreate": Suite(
            workloads.workloads["rabbitmq-operator"]["recreate"], "test-rabbitmq-operator/test/time-travel-1.yaml", sieve_modes.TIME_TRAVEL),
        "resize-pvc": Suite(
            workloads.workloads["rabbitmq-operator"]["resize-pvc"], "test-rabbitmq-operator/test/time-travel-2.yaml", sieve_modes.TIME_TRAVEL, two_sided=True),
        "scaleup-scaledown": Suite(
            workloads.workloads["rabbitmq-operator"]["scaleup-scaledown"], "test-rabbitmq-operator/test/obs-gap-1.yaml", sieve_modes.OBS_GAP),
        "resize-pvc-atomic": Suite(
            workloads.workloads["rabbitmq-operator"]["resize-pvc-atomic"], "test-rabbitmq-operator/test/atomic-1.yaml", sieve_modes.ATOM_VIO, pvc_resize=True)
    },
    "mongodb-operator": {
        "recreate": Suite(
            workloads.workloads["mongodb-operator"]["recreate"], "test-mongodb-operator/test/time-travel-1.yaml", sieve_modes.TIME_TRAVEL, num_workers=3),
        "disable-enable-shard": Suite(
            workloads.workloads["mongodb-operator"]["disable-enable-shard"], "test-mongodb-operator/test/time-travel-2.yaml", sieve_modes.TIME_TRAVEL, num_workers=3),
        "disable-enable-arbiter": Suite(
            workloads.workloads["mongodb-operator"]["disable-enable-arbiter"], "test-mongodb-operator/test/time-travel-3.yaml", sieve_modes.TIME_TRAVEL, num_workers=5),
    },
    "cass-operator": {
        "recreate": Suite(
            workloads.workloads["cass-operator"]["recreate"], "test-cass-operator/test/time-travel-1.yaml", sieve_modes.TIME_TRAVEL),
    },
    "casskop-operator": {
        "recreate": Suite(
            workloads.workloads["casskop-operator"]["recreate"], "test-casskop-operator/test/time-travel-1.yaml", sieve_modes.TIME_TRAVEL),
        "reducepdb": Suite(
            workloads.workloads["casskop-operator"]["reducepdb"], "test-casskop-operator/test/time-travel-2.yaml", sieve_modes.TIME_TRAVEL, two_sided=True),
        "nodesperrack": Suite(
            workloads.workloads["casskop-operator"]["nodesperrack"], "test-casskop-operator/test/obs-gap-1.yaml", sieve_modes.OBS_GAP),
        "scaledown-obs-gap": Suite(
            workloads.workloads["casskop-operator"]["scaledown"], "test-casskop-operator/test/obs-gap-2.yaml", sieve_modes.OBS_GAP),
    },
    "xtradb-operator": {
        "recreate": Suite(
            workloads.workloads["xtradb-operator"]["recreate"], "test-xtradb-operator/test/time-travel-1.yaml", sieve_modes.TIME_TRAVEL, num_workers=4),
        "disable-enable-haproxy": Suite(
            workloads.workloads["xtradb-operator"]["disable-enable-haproxy"], "test-xtradb-operator/test/time-travel-2.yaml", sieve_modes.TIME_TRAVEL, num_workers=4),
        "disable-enable-proxysql": Suite(
            workloads.workloads["xtradb-operator"]["disable-enable-proxysql"], "test-xtradb-operator/test/time-travel-3.yaml", sieve_modes.TIME_TRAVEL, num_workers=4),
    },
    "yugabyte-operator": {
        "recreate": Suite(
            workloads.workloads["yugabyte-operator"]["recreate"], "null", sieve_modes.TIME_TRAVEL),
        "disable-enable-tls": Suite(
            workloads.workloads["yugabyte-operator"]["disable-enable-tls"], "test-yugabyte-operator/test/time-travel-tls.yaml", sieve_modes.TIME_TRAVEL),
        "disable-enable-tserverUIPort": Suite(
            workloads.workloads["yugabyte-operator"]["disable-enable-tserverUIPort"], "test-yugabyte-operator/test/time-travel-tserverUIPort.yaml", sieve_modes.TIME_TRAVEL),
    },
    "nifikop-operator": {
        "change-config": Suite(
            workloads.workloads["nifikop-operator"]["change-config"], "test-nifikop-operator/test/atomic-1.yaml", sieve_modes.ATOM_VIO
        ),
    },
}

# This should be all lower case
# TODO: we should make the CRD checking in learn client case insensitive
CRDs = {
    "cassandra-operator": ["cassandradatacenter", "cassandracluster", "cassandrabackup"],
    "zookeeper-operator": ["zookeepercluster"],
    "rabbitmq-operator": ["rabbitmqcluster"],
    "mongodb-operator": ["perconaservermongodb", "perconaservermongodbbackup", "perconaservermongodbrestore"],
    "cass-operator": ["cassandradatacenter"],
    "casskop-operator": ["cassandracluster", "cassandrarestore", "cassandrabackup"],
    "xtradb-operator": ["perconaxtradbcluster", "perconaxtradbclusterbackup", "perconaxtradbclusterrestore", "perconaxtradbbackup"],
    "yugabyte-operator": ["ybcluster"],
    "nifikop-operator": ["nificluster"],
}

deployment_name = {
    "cassandra-operator": "cassandra-operator",
    "zookeeper-operator": "zookeeper-operator",
    "rabbitmq-operator": "rabbitmq-operator",
    "mongodb-operator": "percona-server-mongodb-operator",
    "cass-operator": "cass-operator",
    "casskop-operator": "casskop-operator",
    "xtradb-operator": "percona-xtradb-cluster-operator",
    "yugabyte-operator": "yugabyte-operator",
    "nifikop-operator": "nifikop-operator",
}

operator_pod_label = {
    "cassandra-operator": "cassandra-operator",
    "zookeeper-operator": "zookeeper-operator",
    "rabbitmq-operator": "rabbitmq-operator",
    "mongodb-operator": "mongodb-operator",
    "cass-operator": "cass-operator",
    "casskop-operator": "casskop-operator",
    "xtradb-operator": "xtradb-operator",
    "yugabyte-operator": "yugabyte-operator",
    "nifikop-operator": "nifikop-operator",
}

controller_runtime_version = {
    "cassandra-operator": "v0.4.0",
    "zookeeper-operator": "v0.5.2",
    "rabbitmq-operator": "v0.8.3",
    "mongodb-operator": "v0.5.2",
    "cass-operator": "v0.5.2",
    "casskop-operator": "v0.6.0",
    "xtradb-operator": "v0.6.2",
    "yugabyte-operator": "v0.5.2",
    "nifikop-operator": "v0.7.2",
}

client_go_version = {
    "cassandra-operator": "v0.0.0-20190918160344-1fbdaa4c8d90",
    "zookeeper-operator": "v0.17.2",
    "rabbitmq-operator": "v0.20.2",
    "mongodb-operator": "v0.17.2",
    "cass-operator": "v0.17.4",
    "casskop-operator": "v0.18.2",
    "xtradb-operator": "v0.18.6",
    "yugabyte-operator": "v0.17.4",
    "nifikop-operator": "v0.20.2",
}

sha = {
    "cassandra-operator": "fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd",
    "zookeeper-operator": "cda03d2f270bdfb51372192766123904f6d88278",
    "rabbitmq-operator": "4f13b9a942ad34fece0171d2174aa0264b10e947",
    "mongodb-operator": "c12b69e2c41efc67336a890039394250420f60bb",
    "cass-operator": "dbd4f7a10533bb2298aed0d40ea20bfd8c133da2",
    "casskop-operator": "f87c8e05c1a2896732fc5f3a174f1eb99e936907",
    "xtradb-operator": "29092c9b145af6eaf5cbff534287483bec4167b6",
    "yugabyte-operator": "966ef1978ed5d714119548b2c4343925fe49f882",
    "nifikop-operator": "1546e0242107bf2f2c1256db50f47c79956dd1c6",
}

docker_file = {
    "cassandra-operator": "docker/cassandra-operator/Dockerfile",
    "zookeeper-operator": "Dockerfile",
    "rabbitmq-operator": "Dockerfile",
    "mongodb-operator": "build/Dockerfile",
    "cass-operator": "operator/docker/base/Dockerfile",
    "casskop-operator": "build/Dockerfile",
    "xtradb-operator": "build/Dockerfile",
    "yugabyte-operator": "build/Dockerfile",
    "nifikop-operator": "Dockerfile",
}


def make_safe_filename(filename):
    return re.sub(r'[^\w\d-]', '_', filename)


def replace_docker_repo(path, dr, dt):
    fin = open(path)
    data = fin.read()
    data = data.replace("${SIEVE-DR}", dr)
    data = data.replace("${SIEVE-DT}", dt)
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


def xtradb_operator_deploy(dr, dt):
    new_path = replace_docker_repo(
        "test-xtradb-operator/deploy/bundle.yaml", dr, dt)
    os.system("kubectl apply -f %s" % new_path)
    os.system("rm %s" % new_path)


def yugabyte_operator_deploy(dr, dt):
    new_path = replace_docker_repo(
        "test-yugabyte-operator/deploy/operator.yaml", dr, dt)
    os.system("cp %s .." % new_path)
    os.system(
        "kubectl create -f test-yugabyte-operator/deploy/crds/yugabyte.com_ybclusters_crd.yaml")
    os.system("kubectl create -f %s" % new_path)
    os.system("rm %s" % new_path)

def nifikop_operator_deploy(dr, dt):
    # Using helm
    new_path = replace_docker_repo(
        "test-nifikop-operator/deploy/values.yaml", dr, dt)
    os.system("kubectl apply -f test-nifikop-operator/deploy/role.yaml")
    os.system("test-nifikop-operator/deploy/zk.sh")
    os.system(
        "helm install -f %s nifikop-operator test-nifikop-operator/deploy" % (new_path))


deploy = {
    "cassandra-operator": cassandra_operator_deploy,
    "zookeeper-operator": zookeeper_operator_deploy,
    "rabbitmq-operator": rabbitmq_operator_deploy,
    "mongodb-operator": mongodb_operator_deploy,
    "cass-operator": cass_operator_deploy,
    "casskop-operator": casskop_operator_deploy,
    "xtradb-operator": xtradb_operator_deploy,
    "yugabyte-operator": yugabyte_operator_deploy,
    "nifikop-operator": nifikop_operator_deploy,
}
