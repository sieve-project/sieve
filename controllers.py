import os
import re
import workloads
from sieve_common.common import sieve_modes, Suite

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
    "elastic-operator": "https://github.com/elastic/cloud-on-k8s.git",
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
    "elastic-operator": "660bc92fbfca469af552a833d8f6a4834c629649",
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
    "elastic-operator": "app/elastic-operator",
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
    "elastic-operator": "v0.11.0",
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
    "elastic-operator": "v0.23.1",
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
    "elastic-operator": "Dockerfile",
}

test_dir = {
    "cassandra-operator": "examples/cassandra-operator",
    "zookeeper-operator": "examples/zookeeper-operator",
    "rabbitmq-operator": "examples/rabbitmq-operator",
    "mongodb-operator": "examples/mongodb-operator",
    "cass-operator": "examples/cass-operator",
    "casskop-operator": "examples/casskop-operator",
    "xtradb-operator": "examples/xtradb-operator",
    "yugabyte-operator": "examples/yugabyte-operator",
    "nifikop-operator": "examples/nifikop-operator",
    "elastic-operator": "examples/elastic-operator",
}

test_suites = {
    "cass-operator": {
        "recreate": Suite(
            workloads.workloads["cass-operator"]["recreate"],
        ),
        "scaledown-scaleup": Suite(
            workloads.workloads["cass-operator"]["scaledown-scaleup"], num_workers=3
        ),
    },
    "cassandra-operator": {
        "recreate": Suite(
            workloads.workloads["cassandra-operator"]["recreate"],
        ),
        "scaledown-scaleup": Suite(
            workloads.workloads["cassandra-operator"]["scaledown-scaleup"],
        ),
    },
    "casskop-operator": {
        "recreate": Suite(
            workloads.workloads["casskop-operator"]["recreate"],
        ),
        "scaledown-to-zero": Suite(
            workloads.workloads["casskop-operator"]["scaledown-to-zero"],
        ),
        "reducepdb": Suite(
            workloads.workloads["casskop-operator"]["reducepdb"],
        ),
    },
    "mongodb-operator": {
        "recreate": Suite(
            workloads.workloads["mongodb-operator"]["recreate"],
            num_workers=3,
        ),
        "scaleup-scaledown": Suite(
            workloads.workloads["mongodb-operator"]["scaleup-scaledown"],
            num_workers=5,
        ),
        "disable-enable-shard": Suite(
            workloads.workloads["mongodb-operator"]["disable-enable-shard"],
            num_workers=3,
        ),
        "disable-enable-arbiter": Suite(
            workloads.workloads["mongodb-operator"]["disable-enable-arbiter"],
            num_workers=5,
        ),
        "run-cert-manager": Suite(
            workloads.workloads["mongodb-operator"]["run-cert-manager"],
            num_workers=3,
        ),
    },
    "nifikop-operator": {
        "recreate": Suite(
            workloads.workloads["nifikop-operator"]["recreate"],
        ),
        "scaledown-scaleup": Suite(
            workloads.workloads["nifikop-operator"]["scaledown-scaleup"],
        ),
        "change-config": Suite(
            workloads.workloads["nifikop-operator"]["change-config"],
        ),
    },
    "rabbitmq-operator": {
        "recreate": Suite(
            workloads.workloads["rabbitmq-operator"]["recreate"],
        ),
        "scaleup-scaledown": Suite(
            workloads.workloads["rabbitmq-operator"]["scaleup-scaledown"],
        ),
        "resize-pvc": Suite(
            workloads.workloads["rabbitmq-operator"]["resize-pvc"],
            use_csi_driver=True,
        ),
    },
    "xtradb-operator": {
        "recreate": Suite(
            workloads.workloads["xtradb-operator"]["recreate"],
            num_workers=4,
        ),
        "disable-enable-haproxy": Suite(
            workloads.workloads["xtradb-operator"]["disable-enable-haproxy"],
            num_workers=4,
        ),
        "disable-enable-proxysql": Suite(
            workloads.workloads["xtradb-operator"]["disable-enable-proxysql"],
            num_workers=4,
        ),
        "run-cert-manager": Suite(
            workloads.workloads["xtradb-operator"]["run-cert-manager"],
            num_workers=4,
        ),
        "scaleup-scaledown": Suite(
            workloads.workloads["xtradb-operator"]["scaleup-scaledown"],
            num_workers=5,
        ),
    },
    "yugabyte-operator": {
        "recreate": Suite(
            workloads.workloads["yugabyte-operator"]["recreate"],
        ),
        "scaleup-scaledown-tserver": Suite(
            workloads.workloads["yugabyte-operator"]["scaleup-scaledown-tserver"],
        ),
        "disable-enable-tls": Suite(
            workloads.workloads["yugabyte-operator"]["disable-enable-tls"],
        ),
        "disable-enable-tuiport": Suite(
            workloads.workloads["yugabyte-operator"]["disable-enable-tuiport"],
        ),
    },
    "zookeeper-operator": {
        "recreate": Suite(
            workloads.workloads["zookeeper-operator"]["recreate"],
        ),
        "scaledown-scaleup": Suite(
            workloads.workloads["zookeeper-operator"]["scaledown-scaleup"],
        ),
    },
}

# This should be all lower case
# TODO: we should make the CRD checking in learn client case insensitive
CRDs = {
    "cassandra-operator": [
        "cassandradatacenter",
        "cassandracluster",
        "cassandrabackup",
    ],
    "zookeeper-operator": ["zookeepercluster"],
    "rabbitmq-operator": ["rabbitmqcluster"],
    "mongodb-operator": [
        "perconaservermongodb",
        "perconaservermongodbbackup",
        "perconaservermongodbrestore",
    ],
    "cass-operator": ["cassandradatacenter"],
    "casskop-operator": ["cassandracluster", "cassandrarestore", "cassandrabackup"],
    "xtradb-operator": [
        "perconaxtradbcluster",
        "perconaxtradbclusterbackup",
        "perconaxtradbclusterrestore",
        "perconaxtradbbackup",
    ],
    "yugabyte-operator": ["ybcluster"],
    "nifikop-operator": ["nificluster"],
    "elastic-operator": ["elasticsearch"],
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
    "elastic-operator": "elastic-operator",
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
    "elastic-operator": "elastic-operator",
}

event_mask = {
    "mongodb-operator": {
        "*": {
            "pod": [
                "mongodb-cluster-rs0-0",
                "mongodb-cluster-rs0-1",
                "mongodb-cluster-rs0-2",
            ]
        }
    },
    "xtradb-operator": {
        "*": {
            "pod": [
                "xtradb-cluster-pxc-0",
                "xtradb-cluster-pxc-1",
                "xtradb-cluster-pxc-2",
            ]
        }
    },
    "yugabyte-operator": {"*": {"pod": ["yb-master-0", "yb-master-1", "yb-master-2"]}},
}

state_mask = {
    # "yugabyte-operator": {
    #     "pod": {"*": {"yb-master-0": {}, "yb-master-1": {}, "yb-master-2": {}}}
    # },
    "nifikop-operator": {
        "nificluster/default/simplenifi": set(
            ["status/state", "status/prometheusReportingTask/version"]
        )
    },
}


def make_safe_filename(filename):
    return re.sub(r"[^\w\d-]", "_", filename)


def replace_docker_repo(path, dr, dt):
    fin = open(path)
    data = fin.read()
    data = data.replace("${SIEVE-DR}", dr)
    data = data.replace("${SIEVE-DT}", dt)
    fin.close()
    tokens = path.rsplit(".", 1)
    new_path = tokens[0] + "-" + make_safe_filename(dr) + "." + tokens[1]
    fin = open(new_path, "w")
    fin.write(data)
    fin.close()
    return new_path


def cassandra_operator_deploy(dr, dt):
    new_path = replace_docker_repo(
        "examples/cassandra-operator/deploy/bundle.yaml", dr, dt
    )
    os.system("kubectl apply -f examples/cassandra-operator/deploy/crds.yaml")
    os.system("kubectl apply -f %s" % new_path)
    os.system("rm %s" % new_path)


def zookeeper_operator_deploy(dr, dt):
    new_path = replace_docker_repo(
        "examples/zookeeper-operator/deploy/default_ns/operator.yaml", dr, dt
    )
    os.system("kubectl create -f examples/zookeeper-operator/deploy/crds")
    os.system(
        "kubectl create -f examples/zookeeper-operator/deploy/default_ns/rbac.yaml"
    )
    os.system("kubectl create -f %s" % new_path)
    os.system("rm %s" % new_path)


def rabbitmq_operator_deploy(dr, dt):
    new_path = replace_docker_repo(
        "examples/rabbitmq-operator/deploy/cluster-operator.yaml", dr, dt
    )
    os.system("kubectl apply -f %s" % new_path)
    os.system("rm %s" % new_path)


def mongodb_operator_deploy(dr, dt):
    new_path = replace_docker_repo(
        "examples/mongodb-operator/deploy/bundle.yaml", dr, dt
    )
    os.system("kubectl apply -f %s" % new_path)
    os.system("rm %s" % new_path)


def cass_operator_deploy(dr, dt):
    new_path = replace_docker_repo(
        "examples/cass-operator/deploy/controller-manifest.yaml", dr, dt
    )
    os.system("kubectl apply -f %s" % new_path)
    os.system("kubectl apply -f examples/cass-operator/deploy/storageClass.yaml")
    os.system("rm %s" % new_path)


def casskop_operator_deploy(dr, dt):
    # Using helm
    new_path = replace_docker_repo(
        "examples/casskop-operator/deploy/values.yaml", dr, dt
    )
    os.system(
        "helm install -f %s casskop-operator examples/casskop-operator/deploy"
        % (new_path)
    )
    os.system("rm %s" % new_path)


def xtradb_operator_deploy(dr, dt):
    new_path = replace_docker_repo(
        "examples/xtradb-operator/deploy/bundle.yaml", dr, dt
    )
    os.system("kubectl apply -f %s" % new_path)
    os.system("rm %s" % new_path)


def yugabyte_operator_deploy(dr, dt):
    new_path = replace_docker_repo(
        "examples/yugabyte-operator/deploy/operator.yaml", dr, dt
    )
    os.system(
        "kubectl create -f examples/yugabyte-operator/deploy/crds/yugabyte.com_ybclusters_crd.yaml"
    )
    os.system("kubectl create -f %s" % new_path)
    os.system("rm %s" % new_path)


def nifikop_operator_deploy(dr, dt):
    # Using helm
    new_path = replace_docker_repo(
        "examples/nifikop-operator/deploy/values.yaml", dr, dt
    )
    os.system("kubectl apply -f examples/nifikop-operator/deploy/role.yaml")
    os.system("examples/nifikop-operator/deploy/zk.sh")
    os.system(
        "helm install -f %s nifikop-operator examples/nifikop-operator/deploy"
        % (new_path)
    )
    os.system("rm %s" % (new_path))

def elastic_operator_deploy(dr, dt):
    new_path = replace_docker_repo(
        "examples/elastic-operator/deploy/operator.yaml", dr, dt
    )
    os.system("kubectl create -f examples/elastic-operator/deploy/crds.yaml")
    os.system("kubectl apply -f %s" % new_path)
    os.system("rm %s" % (new_path))

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
    "elastic-operator": elastic_operator_deploy,
}
