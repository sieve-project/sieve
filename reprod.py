import optparse
import sieve_config
import os
from common import cprint, bcolors

reprod_map = {
    "cassandra-operator": {
        "obs-gap-1": ["scaledown-scaleup", "cassandra1_obs_gap_1.yaml"],
        "time-travel-1": ["recreate", "cassandra1_time_travel_1.yaml"],
        "time-travel-2": ["scaledown-scaleup", "cassandra1_time_travel_2.yaml"],
    },
    "cass-operator": {
        "time-travel-1": ["recreate", "cassandra2_time_travel_1.yaml"],
    },
    "casskop-operator": {
        "atom-vio-1": ["scaledown-to-zero", "cassandra3_atom_vio_1.yaml"],
        "obs-gap-1": ["scaledown-to-zero", "cassandra3_obs_gap_1.yaml"],
        "time-travel-1": ["recreate", "cassandra3_time_travel_1.yaml"],
        "time-travel-2": ["reducepdb", "cassandra3_time_travel_2.yaml"],
    },
    "nifikop-operator": {
        "atom-vio-1": ["change-config", "nifi_atom_vio_1.yaml"],
    },
    "rabbitmq-operator": {
        "atom-vio-1": ["resize-pvc", "rabbitmq_atom_vio_1.yaml"],
        "obs-gap-1": ["scaleup-scaledown", "rabbitmq_obs_gap_1.yaml"],
        "time-travel-1": ["recreate", "rabbitmq_time_travel_1.yaml"],
        "time-travel-2": ["resize-pvc", "rabbitmq_time_travel_2.yaml"],
    },
    "mongodb-operator": {
        "atom-vio-1": ["disable-enable-shard", "mongodb_atom_vio_1.yaml"],
        "atom-vio-2": ["run-cert-manager", "mongodb_atom_vio_2.yaml"],
        "obs-gap-1": ["disable-enable-arbiter", "mongodb_obs_gap_1.yaml"],
        "time-travel-1": ["recreate", "mongodb_time_travel_1.yaml"],
        "time-travel-2": ["disable-enable-shard", "mongodb_time_travel_2.yaml"],
        "time-travel-3": ["disable-enable-arbiter", "mongodb_time_travel_3.yaml"],
    },
    "xtradb-operator": {
        "atom-vio-1": ["disable-enable-proxysql", "xtradb_atom_vio_1.yaml"],
        "atom-vio-2": ["run-cert-manager", "xtradb_atom_vio_2.yaml"],
        "time-travel-1": ["recreate", "xtradb_time_travel_1.yaml"],
        "time-travel-2": ["disable-enable-haproxy", "xtradb_time_travel_2.yaml"],
        "time-travel-3": ["disable-enable-proxysql", "xtradb_time_travel_3.yaml"],
    },
    "yugabyte-operator": {
        "obs-gap-1": ["scaleup-scaledown-tserver", "yugabyte_obs_gap_1.yaml"],
        "time-travel-1": ["disable-enable-tls", "yugabyte_time_travel_1.yaml"],
        "time-travel-2": ["disable-enable-tuiport", "yugabyte_time_travel_2.yaml"],
    },
    "zookeeper-operator": {
        "time-travel-1": ["recreate", "zookeeper_time_travel_1.yaml"],
        "time-travel-2": ["scaledown-scaleup", "zookeeper_time_travel_2.yaml"],
    },
}


def reproduce_single_bug(operator, bug, docker, phase):
    mode = bug[:-2]
    test = reprod_map[operator][bug][0]
    config = os.path.join("reprod", reprod_map[operator][bug][1])
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
        help="run the PHASE: setup_only, workload_only, check_only or all",
        metavar="PHASE",
        default="all",
    )

    parser.add_option(
        "-d",
        "--docker",
        dest="docker",
        help="DOCKER repo that you have access",
        metavar="DOCKER",
        default=sieve_config.config["docker_repo"],
    )

    (options, args) = parser.parse_args()

    if options.project is None:
        parser.error("parameter project required")

    if options.bug is None and options.project != "all":
        parser.error("parameter bug required")

    if options.project == "all":
        for operator in reprod_map:
            for bug in reprod_map[operator]:
                reproduce_bug(operator, bug, options.docker, options.phase)
    else:
        reproduce_bug(options.project, options.bug, options.docker, options.phase)
