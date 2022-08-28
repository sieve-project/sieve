import sys

sys.path.append("../")

import argparse
import os

controllers_to_run = {
    "cassandra-operator": ["recreate", "scaledown-scaleup"],
    "zookeeper-operator": ["recreate", "scaledown-scaleup"],
    "rabbitmq-operator": ["recreate", "scaleup-scaledown", "resize-pvc"],
    "mongodb-operator": [
        "recreate",
        "scaleup-scaledown",
        "disable-enable-shard",
        "disable-enable-arbiter",
        "run-cert-manager",
    ],
    "cass-operator": ["recreate", "scaledown-scaleup"],
    "casskop-operator": ["recreate", "scaledown-to-zero", "reducepdb"],
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
    "nifikop-operator": ["recreate", "scaledown-scaleup", "change-config"],
    "elastic-operator": ["recreate", "scaledown-scaleup"],
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automate learning run.")
    parser.add_argument(
        "-d",
        dest="docker",
        help="Docker account",
        default="ghcr.io/sieve-project/action",
    )
    parser.add_argument("-c", dest="controllers", help="Controllers to test", nargs="+")
    args = parser.parse_args()
    os.chdir("..")

    if args.controllers is None:
        print("No controller specified, running learning mode for all controllers")
        controllers = controllers_to_run.keys()
    else:
        controllers = args.controllers

    os.system("docker pull %s/node:learn" % "ghcr.io/sieve-project/action")
    for controller in controllers:
        os.system(
            "docker pull %s/%s:learn" % ("ghcr.io/sieve-project/action", controller)
        )
        for testcase in controllers_to_run[controller]:
            os.system(
                "python3 sieve.py -m learn-once -c {} -w {} -r {}".format(
                    controller, testcase, "ghcr.io/sieve-project/action"
                )
            )
