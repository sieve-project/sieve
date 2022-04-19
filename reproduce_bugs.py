import optparse
from sieve_common.default_config import get_common_config
import os
import json
import time
from sieve_common.common import cprint, bcolors


def before_reproducing_yugabyte_operator_indirect_1():
    current_crd = (
        "examples/yugabyte-operator/deploy/crds/yugabyte.com_ybclusters_crd.yaml"
    )
    bkp_crd = (
        "examples/yugabyte-operator/deploy/crds/yugabyte.com_ybclusters_crd.yaml.bkp"
    )
    os.system("cp {} {}".format(current_crd, bkp_crd))
    fin = open(current_crd)
    data = fin.read()
    data = data.replace("# minimum: 1", "minimum: 1")
    fin.close()
    fout = open(current_crd, "w")
    fout.write(data)
    fout.close()


def after_reproducing_yugabyte_operator_indirect_1():
    current_crd = (
        "examples/yugabyte-operator/deploy/crds/yugabyte.com_ybclusters_crd.yaml"
    )
    bkp_crd = (
        "examples/yugabyte-operator/deploy/crds/yugabyte.com_ybclusters_crd.yaml.bkp"
    )
    os.system("mv {} {}".format(bkp_crd, current_crd))


def before_reproducing_cassandra_operator_indirect_1():
    current_cfg = "examples/cassandra-operator/config.json"
    bkp_cfg = "examples/cassandra-operator/config.json.bkp"
    os.system("cp {} {}".format(current_cfg, bkp_cfg))
    data = json.load(open(current_cfg))
    del data["cherry_pick_commits"]
    json.dump(data, open(current_cfg, "w"), indent=4)
    print(
        "building cassandra-operator image without the fix of https://github.com/instaclustr/cassandra-operator/issues/400"
    )
    os.system("python3 build.py -p cassandra-operator -m test > /dev/null 2>&1")


def after_reproducing_cassandra_operator_indirect_1():
    current_cfg = "examples/cassandra-operator/config.json"
    bkp_cfg = "examples/cassandra-operator/config.json.bkp"
    os.system("mv {} {}".format(bkp_cfg, current_cfg))
    print(
        "building cassandra-operator image with the fix of https://github.com/instaclustr/cassandra-operator/issues/400"
    )
    os.system("python3 build.py -p cassandra-operator -m test > /dev/null 2>&1")


reprod_map = {
    "cass-operator": {
        "intermediate-state-1": ["recreate", "cass-operator-intermediate-state-1.yaml"],
        "stale-state-1": ["recreate", "cass-operator-stale-state-1.yaml"],
    },
    "cassandra-operator": {
        "stale-state-1": ["recreate", "cassandra-operator-stale-state-1.yaml"],
        "stale-state-2": ["scaledown-scaleup", "cassandra-operator-stale-state-2.yaml"],
        "unobserved-state-1": [
            "scaledown-scaleup",
            "cassandra-operator-unobserved-state-1.yaml",
        ],
        "indirect-1": [
            "scaledown-scaleup",
            "cassandra-operator-indirect-1.yaml",
            before_reproducing_cassandra_operator_indirect_1,
            after_reproducing_cassandra_operator_indirect_1,
        ],
        "indirect-2": [
            "scaledown-scaleup-brittle",
            "cassandra-operator-indirect-2.yaml",
        ],
    },
    "casskop-operator": {
        "intermediate-state-1": [
            "scaledown-to-zero",
            "casskop-intermediate-state-1.yaml",
        ],
        "stale-state-1": ["recreate", "casskop-stale-state-1.yaml"],
        "stale-state-2": ["reducepdb", "casskop-stale-state-2.yaml"],
        "unobserved-state-1": ["scaledown-to-zero", "casskop-unobserved-state-1.yaml"],
    },
    "mongodb-operator": {
        "intermediate-state-1": [
            "disable-enable-shard",
            "mongodb-operator-intermediate-state-1.yaml",
        ],
        "intermediate-state-2": [
            "run-cert-manager",
            "mongodb-operator-intermediate-state-2.yaml",
        ],
        "stale-state-1": ["recreate", "mongodb-operator-stale-state-1.yaml"],
        "stale-state-2": [
            "disable-enable-shard",
            "mongodb-operator-stale-state-2.yaml",
        ],
        "stale-state-3": [
            "disable-enable-arbiter",
            "mongodb-operator-stale-state-3.yaml",
        ],
        "unobserved-state-1": [
            "disable-enable-arbiter",
            "mongodb-operator-unobserved-state-1.yaml",
        ],
        "indirect-1": ["disable-enable-shard", "mongodb-operator-indirect-1.yaml"],
        "indirect-2": ["recreate", "mongodb-operator-indirect-2.yaml"],
        "indirect-3": [
            "disable-enable-shard-brittle",
            "mongodb-operator-indirect-3.yaml",
        ],
    },
    "nifikop-operator": {
        "intermediate-state-1": ["change-config", "nifikop-intermediate-state-1.yaml"],
    },
    "rabbitmq-operator": {
        "intermediate-state-1": [
            "resize-pvc",
            "rabbitmq-operator-intermediate-state-1.yaml",
        ],
        "stale-state-1": ["recreate", "rabbitmq-operator-stale-state-1.yaml"],
        "stale-state-2": ["resize-pvc", "rabbitmq-operator-stale-state-2.yaml"],
        "unobserved-state-1": [
            "scaleup-scaledown",
            "rabbitmq-operator-unobserved-state-1.yaml",
        ],
    },
    "xtradb-operator": {
        "intermediate-state-1": [
            "disable-enable-proxysql",
            "xtradb-operator-intermediate-state-1.yaml",
        ],
        "intermediate-state-2": [
            "run-cert-manager",
            "xtradb-operator-intermediate-state-2.yaml",
        ],
        "stale-state-1": ["recreate", "xtradb-operator-stale-state-1.yaml"],
        "stale-state-2": [
            "disable-enable-haproxy",
            "xtradb-operator-stale-state-2.yaml",
        ],
        "stale-state-3": [
            "disable-enable-proxysql",
            "xtradb-operator-stale-state-3.yaml",
        ],
        "unobserved-state-1": [
            "scaleup-scaledown",
            "xtradb-operator-unobserved-state-1.yaml",
        ],
    },
    "yugabyte-operator": {
        "stale-state-1": ["disable-enable-tls", "yugabyte-operator-stale-state-1.yaml"],
        "stale-state-2": [
            "disable-enable-tuiport",
            "yugabyte-operator-stale-state-2.yaml",
        ],
        "unobserved-state-1": [
            "scaleup-scaledown-tserver",
            "yugabyte-operator-unobserved-state-1.yaml",
        ],
        "indirect-1": [
            "disable-enable-tuiport",
            "yugabyte-operator-indirect-1.yaml",
            before_reproducing_yugabyte_operator_indirect_1,
            after_reproducing_yugabyte_operator_indirect_1,
        ],
        "indirect-2": ["disable-enable-tls", "yugabyte-operator-indirect-2.yaml"],
    },
    "zookeeper-operator": {
        "stale-state-1": ["recreate", "zookeeper-operator-stale-state-1.yaml"],
        "stale-state-2": ["scaledown-scaleup", "zookeeper-operator-stale-state-2.yaml"],
        "indirect-1": ["recreate", "zookeeper-operator-indirect-1.yaml"],
    },
}


def reproduce_single_bug(operator, bug, docker, phase, skip):
    before_reproduce = None
    after_reproduce = None
    if len(reprod_map[operator][bug]) >= 3 and reprod_map[operator][bug][2] is not None:
        before_reproduce = reprod_map[operator][bug][2]
    if len(reprod_map[operator][bug]) == 4 and reprod_map[operator][bug][3] is not None:
        after_reproduce = reprod_map[operator][bug][3]
    if before_reproduce is not None:
        before_reproduce()
    test_name = reprod_map[operator][bug][0]
    config = os.path.join("bug_reproduction_test_plans", reprod_map[operator][bug][1])
    sieve_cmd = "python3 sieve.py -p %s -c %s -d %s --phase=%s" % (
        operator,
        config,
        docker,
        phase,
    )
    cprint(sieve_cmd, bcolors.OKGREEN)
    if not skip:
        os.system(sieve_cmd)
    else:
        cprint("skip this command", bcolors.OKGREEN)
    if after_reproduce is not None:
        after_reproduce()
    test_result_file = "sieve_test_results/{}-{}-{}.json".format(
        operator,
        test_name,
        os.path.basename(config),
    )
    cprint(
        "Please refer to {} for more detailed information".format(test_result_file),
        bcolors.OKGREEN,
    )
    test_result = json.load(open(test_result_file))
    content = test_result[operator][test_name]["test"][config]
    if content["number_errors"] > 0:
        return {"reproduced": True, "test-result-file": test_result_file}
    else:
        return {"reproduced": False, "test-result-file": test_result_file}


def reproduce_bug(operator, bug, docker, phase, skip):
    stats_map = {}
    if bug == "all":
        for b in reprod_map[operator]:
            if "indirect" in b:
                continue
            stats_map[b] = reproduce_single_bug(operator, b, docker, phase, skip)
    elif (
        bug == "intermediate-state"
        or bug == "unobserved-state"
        or bug == "stale-state"
        or bug == "indirect"
    ):
        for b in reprod_map[operator]:
            if b.startswith(bug):
                stats_map[b] = reproduce_single_bug(operator, b, docker, phase, skip)
    else:
        stats_map[bug] = reproduce_single_bug(operator, bug, docker, phase, skip)
    return stats_map


def generate_table3():
    bug_stats = {}
    f = open("bug_reproduction_stats.tsv")
    f.readline()
    is_cnt = 0
    ss_cnt = 0
    us_cnt = 0
    for line in f.readlines():
        tokens = line.strip().split("\t")
        controller = tokens[0]
        bug = tokens[1]
        if controller not in bug_stats:
            bug_stats[controller] = {
                "intermediate-state": 0,
                "stale-state": 0,
                "unobserved-state": 0,
            }
        if bug.startswith("intermediate-state"):
            bug_stats[controller]["intermediate-state"] += 1
            is_cnt += 1
        elif bug.startswith("stale-state"):
            bug_stats[controller]["stale-state"] += 1
            ss_cnt += 1
        elif bug.startswith("unobserved-state"):
            bug_stats[controller]["unobserved-state"] += 1
            us_cnt += 1
        table = "Controller\tIntermediate-State\tStale-State\tUnobserved-State\n"
        for controller in bug_stats:
            controller_in_table = controller
            # handle the naming incompability between script and the paper
            # casskop-operator => casskop in paper
            # nifikop-operator => nifikop in paper
            if controller == "casskop-operator" or controller == "nifikop-operator":
                controller_in_table = controller.split("-")[0]
            table += "{}\t{}\t{}\t{}\n".format(
                controller_in_table,
                bug_stats[controller]["intermediate-state"],
                bug_stats[controller]["stale-state"],
                bug_stats[controller]["unobserved-state"],
            )
        table += "Total\t{}\t{}\t{}\n".format(is_cnt, ss_cnt, us_cnt)
        open("table3.tsv", "w").write(table)


def backup_old_results():
    timestamp = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
    if os.path.exists("sieve_test_results"):
        os.system("cp -r sieve_test_results/ sieve_test_results.{}/".format(timestamp))
    if os.path.exists("bug_reproduction_stats.tsv"):
        os.system(
            "cp bug_reproduction_stats.tsv bug_reproduction_stats.{}.tsv".format(
                timestamp
            )
        )
    if os.path.exists("table3.tsv"):
        os.system("cp table3.tsv table3.{}.tsv".format(timestamp))


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
        default="all",
    )

    parser.add_option(
        "-b",
        "--bug",
        dest="bug",
        help="BUG that you want to reproduce",
        metavar="BUG",
        default="all",
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

    parser.add_option(
        "-s",
        "--skip",
        dest="skip",
        action="store_true",
        help="SKIP running Sieve",
        metavar="DOCKER",
        default=False,
    )

    (options, args) = parser.parse_args()

    if options.project is None:
        parser.error("parameter project required")

    if options.bug is None and options.project != "all":
        parser.error("parameter bug required")

    backup_old_results()

    if not options.skip:
        os.system("rm -rf sieve_test_results")

    stats_map = {}
    if options.project == "all":
        for operator in reprod_map:
            stats_map[operator] = reproduce_bug(
                operator, options.bug, options.docker, options.phase, options.skip
            )
    else:
        stats_map[options.project] = reproduce_bug(
            options.project, options.bug, options.docker, options.phase, options.skip
        )

    table = "controller\tbug\treproduced\ttest-result-file\n"
    for controller in stats_map:
        for bug in stats_map[controller]:
            table += "{}\t{}\t{}\t{}\n".format(
                controller,
                bug,
                stats_map[controller][bug]["reproduced"],
                stats_map[controller][bug]["test-result-file"],
            )
    open("bug_reproduction_stats.tsv", "w").write(table)
    if options.project == "all" and options.bug == "all":
        generate_table3()
