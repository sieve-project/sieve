import os
import json
import optparse
import time
from sieve_common.default_config import get_common_config
from sieve_common.common import cprint, bcolors

controllers_to_check = {
    "cass-operator": ["recreate", "scaledown-scaleup"],
    "cassandra-operator": ["recreate", "scaledown-scaleup"],
    "casskop-operator": ["recreate", "scaledown-to-zero", "reducepdb"],
    "mongodb-operator": [
        "recreate",
        "scaleup-scaledown",
        "disable-enable-shard",
        "disable-enable-arbiter",
        "run-cert-manager",
    ],
    "nifikop-operator": ["recreate", "scaledown-scaleup", "change-config"],
    "rabbitmq-operator": ["recreate", "scaleup-scaledown", "resize-pvc"],
    "xtradb-operator": [
        "recreate",
        "disable-enable-haproxy",
        "disable-enable-proxysql",
        "run-cert-manager",
        "scaleup-scaledown",
    ],
    "yugabyte-operator": [
        "recreate",
        "scaleup-scaledown-tserver",
        "disable-enable-tls",
        "disable-enable-tuiport",
    ],
    "zookeeper-operator": ["recreate", "scaledown-scaleup"],
}


def generate_test_plan_stat(log, controller, docker, phase, times):
    mode = ""
    if times == "once":
        mode = "learn-once"
    else:
        mode = "learn-twice"
    controllers = []
    if controller == "all":
        for selected_controller in controllers_to_check:
            controllers.append(selected_controller)
    else:
        controllers.append(controller)
    for selected_controller in controllers:
        for test_suite in controllers_to_check[selected_controller]:
            sieve_cmd = (
                "python3 sieve.py -l %s -p %s -t %s -d %s -s learn -m %s --phase=%s"
                % (
                    log,
                    selected_controller,
                    test_suite,
                    docker,
                    mode,
                    phase,
                )
            )
            cprint(sieve_cmd, bcolors.OKGREEN)
            os.system(sieve_cmd)
            time.sleep(10)
    stats_map = {}
    for controller in controllers:
        stats_map[controller] = {
            "baseline": 0,
            "after_p1": 0,
            "after_p2": 0,
            "final": 0,
        }
        for test in controllers_to_check[controller]:
            result_filename = "sieve_learn_results/{}-{}.json".format(controller, test)
            result_map = json.load(open(result_filename))
            stats_map[controller]["baseline"] += result_map["intermediate-state"][
                "baseline"
            ]
            stats_map[controller]["baseline"] += result_map["stale-state"]["baseline"]
            stats_map[controller]["baseline"] += result_map["unobserved-state"][
                "baseline"
            ]
            stats_map[controller]["after_p1"] += result_map["intermediate-state"][
                "after_p1"
            ]
            stats_map[controller]["after_p1"] += result_map["stale-state"]["after_p1"]
            stats_map[controller]["after_p1"] += result_map["unobserved-state"][
                "after_p1"
            ]
            stats_map[controller]["after_p2"] += result_map["intermediate-state"][
                "after_p2"
            ]
            stats_map[controller]["after_p2"] += result_map["stale-state"]["after_p2"]
            stats_map[controller]["after_p2"] += result_map["unobserved-state"][
                "after_p2"
            ]
            stats_map[controller]["final"] += result_map["intermediate-state"]["final"]
            stats_map[controller]["final"] += result_map["stale-state"]["final"]
            stats_map[controller]["final"] += result_map["unobserved-state"]["final"]

    table = "controller\tbaseline\tprune-by-causality\tprune-updates\tdeterministic-timing\n"
    for controller in controllers:
        table += "{}\t{}\t{}\t{}\t{}\n".format(
            controller,
            stats_map[controller]["baseline"],
            stats_map[controller]["after_p1"],
            stats_map[controller]["after_p2"],
            stats_map[controller]["final"],
        )
    open("test_plan_stats.tsv", "w").write(table)


if __name__ == "__main__":
    common_config = get_common_config()
    usage = "usage: python3 sieve.py [options]"
    parser = optparse.OptionParser(usage=usage)

    parser.add_option(
        "-l",
        "--log",
        dest="log",
        help="specify LOG that contains the controller trace",
        metavar="LOG",
        default="log_for_learning",
    )

    parser.add_option(
        "-p",
        "--project",
        dest="project",
        help="specify PROJECT to generate test plans",
        metavar="PROJECT",
        default="all",
    )

    parser.add_option(
        "--phase",
        dest="phase",
        help="run the PHASE: setup, workload, check or all",
        metavar="PHASE",
        default="check",
    )

    parser.add_option(
        "--times",
        dest="times",
        help="how many TIMES to run the workloads: once, twice",
        metavar="TIMES",
        default="once",
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

    os.system("rm -rf sieve_learn_results")
    generate_test_plan_stat(
        options.log, options.project, options.docker, options.phase, options.times
    )
