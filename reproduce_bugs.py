import optparse
from sieve_common.default_config import get_common_config
import os
from sieve_common.common import cprint, bcolors

reprod_map = {
    "cassandra-operator": {
        "unobserved-state-1": ["scaledown-scaleup", "cassandra-operator-unobserved-state-1.yaml"],
        "stale-state-1": ["recreate", "cassandra-operator-stale-state-1.yaml"],
        "stale-state-2": ["scaledown-scaleup", "cassandra-operator-stale-state-2.yaml"],
    },
    "cass-operator": {
        "intermediate-state-1": ["recreate", "cass-operator-intermediate-state-1.yaml"],
        "stale-state-1": ["recreate", "cass-operator-stale-state-1.yaml"],
    },
    "casskop-operator": {
        "intermediate-state-1": ["scaledown-to-zero", "casskop-intermediate-state-1.yaml"],
        "unobserved-state-1": ["scaledown-to-zero", "casskop-unobserved-state-1.yaml"],
        "stale-state-1": ["recreate", "casskop-stale-state-1.yaml"],
        "stale-state-2": ["reducepdb", "casskop-stale-state-2.yaml"],
    },
    "nifikop-operator": {
        "intermediate-state-1": ["change-config", "nifikop-intermediate-state-1.yaml"],
    },
    "rabbitmq-operator": {
        "intermediate-state-1": ["resize-pvc", "rabbitmq-operator-intermediate-state-1.yaml"],
        "unobserved-state-1": ["scaleup-scaledown", "rabbitmq-operator-unobserved-state-1.yaml"],
        "stale-state-1": ["recreate", "rabbitmq-operator-stale-state-1.yaml"],
        "stale-state-2": ["resize-pvc", "rabbitmq-operator-stale-state-2.yaml"],
    },
    "mongodb-operator": {
        "intermediate-state-1": ["disable-enable-shard", "mongodb-operator-intermediate-state-1.yaml"],
        "intermediate-state-2": ["run-cert-manager", "mongodb-operator-intermediate-state-2.yaml"],
        "unobserved-state-1": ["disable-enable-arbiter", "mongodb-operator-unobserved-state-1.yaml"],
        "stale-state-1": ["recreate", "mongodb-operator-stale-state-1.yaml"],
        "stale-state-2": ["disable-enable-shard", "mongodb-operator-stale-state-2.yaml"],
        "stale-state-3": ["disable-enable-arbiter", "mongodb-operator-stale-state-3.yaml"],
    },
    "xtradb-operator": {
        "intermediate-state-1": ["disable-enable-proxysql", "xtradb-operator-intermediate-state-1.yaml"],
        "intermediate-state-2": ["run-cert-manager", "xtradb-operator-intermediate-state-2.yaml"],
        "unobserved-state-1": ["scaleup-scaledown", "xtradb-operator-unobserved-state-1.yaml"],
        "stale-state-1": ["recreate", "xtradb-operator-stale-state-1.yaml"],
        "stale-state-2": ["disable-enable-haproxy", "xtradb-operator-stale-state-2.yaml"],
        "stale-state-3": ["disable-enable-proxysql", "xtradb-operator-stale-state-3.yaml"],
    },
    "yugabyte-operator": {
        "unobserved-state-1": ["scaleup-scaledown-tserver", "yugabyte-operator-unobserved-state-1.yaml"],
        "stale-state-1": ["disable-enable-tls", "yugabyte-operator-stale-state-1.yaml"],
        "stale-state-2": ["disable-enable-tuiport", "yugabyte-operator-stale-state-2.yaml"],
    },
    "zookeeper-operator": {
        "stale-state-1": ["recreate", "zookeeper-operator-stale-state-1.yaml"],
        "stale-state-2": ["scaledown-scaleup", "zookeeper-operator-stale-state-2.yaml"],
    },
    "elastic-operator": {
        "stale-state-1": ["recreate", "elastic-operator-stale-state-1.yaml"],
        "stale-state-2": ["scaledown-scaleup", "elastic-operator-stale-state-2.yaml"],
    },
}


def reproduce_single_bug(operator, bug, docker, phase):
    test = reprod_map[operator][bug][0]
    config = os.path.join("bug_reproduction_test_plans", reprod_map[operator][bug][1])
    sieve_cmd = (
        "python3 sieve.py -p %s -s test -m test -t %s -c %s -d %s --phase=%s"
        % (
            operator,
            test,
            config,
            docker,
            phase,
        )
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
    common_config = get_common_config()
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
        default=common_config.docker_registry,
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
