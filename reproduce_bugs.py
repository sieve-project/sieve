import optparse
from sieve_common.default_config import sieve_config
import os
from sieve_common.common import cprint, bcolors

reprod_map = {
    "cassandra-operator": {
        "unobserved-state-1": ["scaledown-scaleup", "cassandra1_unobsr_1.yaml"],
        "stale-state-1": ["recreate", "cassandra1_stale_1.yaml"],
        "stale-state-2": ["scaledown-scaleup", "cassandra1_stale_2.yaml"],
    },
    "cass-operator": {
        "intermediate-state-1": ["recreate", "cassandra2_intmd_1.yaml"],
        "stale-state-1": ["recreate", "cassandra2_stale_1.yaml"],
    },
    "casskop-operator": {
        "intermediate-state-1": ["scaledown-to-zero", "cassandra3_intmd_1.yaml"],
        "unobserved-state-1": ["scaledown-to-zero", "cassandra3_unobsr_1.yaml"],
        "stale-state-1": ["recreate", "cassandra3_stale_1.yaml"],
        "stale-state-2": ["reducepdb", "cassandra3_stale_2.yaml"],
    },
    "nifikop-operator": {
        "intermediate-state-1": ["change-config", "nifi_intmd_1.yaml"],
    },
    "rabbitmq-operator": {
        "intermediate-state-1": ["resize-pvc", "rabbitmq_intmd_1.yaml"],
        "unobserved-state-1": ["scaleup-scaledown", "rabbitmq_unobsr_1.yaml"],
        "stale-state-1": ["recreate", "rabbitmq_stale_1.yaml"],
        "stale-state-2": ["resize-pvc", "rabbitmq_stale_2.yaml"],
    },
    "mongodb-operator": {
        "intermediate-state-1": ["disable-enable-shard", "mongodb_intmd_1.yaml"],
        "intermediate-state-2": ["run-cert-manager", "mongodb_intmd_2.yaml"],
        "unobserved-state-1": ["disable-enable-arbiter", "mongodb_unobsr_1.yaml"],
        "stale-state-1": ["recreate", "mongodb_stale_1.yaml"],
        "stale-state-2": ["disable-enable-shard", "mongodb_stale_2.yaml"],
        "stale-state-3": ["disable-enable-arbiter", "mongodb_stale_3.yaml"],
    },
    "xtradb-operator": {
        "intermediate-state-1": ["disable-enable-proxysql", "xtradb_intmd_1.yaml"],
        "intermediate-state-2": ["run-cert-manager", "xtradb_intmd_2.yaml"],
        "unobserved-state-1": ["scaleup-scaledown", "xtradb_unobsr_1.yaml"],
        "stale-state-1": ["recreate", "xtradb_stale_1.yaml"],
        "stale-state-2": ["disable-enable-haproxy", "xtradb_stale_2.yaml"],
        "stale-state-3": ["disable-enable-proxysql", "xtradb_stale_3.yaml"],
    },
    "yugabyte-operator": {
        "unobserved-state-1": ["scaleup-scaledown-tserver", "yugabyte_unobsr_1.yaml"],
        "stale-state-1": ["disable-enable-tls", "yugabyte_stale_1.yaml"],
        "stale-state-2": ["disable-enable-tuiport", "yugabyte_stale_2.yaml"],
    },
    "zookeeper-operator": {
        "stale-state-1": ["recreate", "zookeeper_stale_1.yaml"],
        "stale-state-2": ["scaledown-scaleup", "zookeeper_stale_2.yaml"],
    },
    "elastic-operator": {
        "stale-state-1": ["recreate", "elastic_stale_1.yaml"],
        "stale-state-2": ["scaledown-scaleup", "elastic_stale_2.yaml"],
    },
}


def reproduce_single_bug(operator, bug, docker, phase):
    mode = bug[:-2]
    test = reprod_map[operator][bug][0]
    config = os.path.join("bug_reproduction_test_plans", reprod_map[operator][bug][1])
    sieve_cmd = "python3 sieve.py -p %s -s test -m %s -t %s -c %s -d %s --phase=%s" % (
        operator,
        mode,
        test,
        config,
        docker,
        phase,
    )
    cprint(sieve_cmd, bcolors.OKGREEN)
    os.system(sieve_cmd)


def reproduce_bug(operator, bug, docker, phase):
    if bug == "all":
        for b in reprod_map[operator]:
            reproduce_single_bug(operator, b, docker, phase)
    elif (
        bug == "intermediate-state" or bug == "unobserved-state" or bug == "stale-state"
    ):
        for b in reprod_map[operator]:
            if b.startswith(bug):
                reproduce_single_bug(operator, b, docker, phase)
    else:
        reproduce_single_bug(operator, bug, docker, phase)


if __name__ == "__main__":
    usage = "usage: python3 sieve.py [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option(
        "-p",
        "--project",
        dest="project",
        help="specify PROJECT to test",
        metavar="PROJECT",
    )

    parser.add_option(
        "-b",
        "--bug",
        dest="bug",
        help="BUG that you want to reproduce",
        metavar="BUG",
    )

    parser.add_option(
        "--phase",
        dest="phase",
        help="run the PHASE: setup, workload, check or all",
        metavar="PHASE",
        default="all",
    )

    parser.add_option(
        "-d",
        "--docker",
        dest="docker",
        help="DOCKER repo that you have access",
        metavar="DOCKER",
        default=sieve_config["docker_repo"],
    )

    (options, args) = parser.parse_args()

    if options.project is None:
        parser.error("parameter project required")

    if options.bug is None and options.project != "all":
        parser.error("parameter bug required")

    if options.project == "all":
        for operator in reprod_map:
            reproduce_bug(operator, options.bug, options.docker, options.phase)
    else:
        reproduce_bug(options.project, options.bug, options.docker, options.phase)
