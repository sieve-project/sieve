import os
import json
import shutil
from sieve_common.config import get_common_config
from evaluation_sanity_check import common

total_result_map = {}


def collect_spec():
    sub_result_map = {}
    for controller in common.controllers_to_check:
        sub_result_map[controller] = {}
        ds_base_cnt = 0
        ms_base_cnt = 0
        ss_base_cnt = 0
        ds_after_p1_cnt = 0
        ms_after_p1_cnt = 0
        ss_after_p1_cnt = 0
        ds_after_p2_cnt = 0
        ms_after_p2_cnt = 0
        ss_after_p2_cnt = 0
        ds_cnt = 0
        ms_cnt = 0
        ss_cnt = 0
        for test in common.controllers_to_check[controller]:
            result_filename = "sieve_learn_results/{}-{}.json".format(controller, test)
            result_map = json.load(open(result_filename))
            ds_base_cnt += result_map["intermediate-state"]["baseline"]
            ds_after_p1_cnt += result_map["intermediate-state"]["after_p1"]
            ds_after_p2_cnt += result_map["intermediate-state"]["after_p2"]
            ds_cnt += result_map["intermediate-state"]["final"]
            ms_base_cnt += result_map["unobserved-state"]["baseline"]
            ms_after_p1_cnt += result_map["unobserved-state"]["after_p1"]
            ms_after_p2_cnt += result_map["unobserved-state"]["after_p2"]
            ms_cnt += result_map["unobserved-state"]["final"]
            ss_base_cnt += result_map["stale-state"]["baseline"]
            ss_after_p1_cnt += result_map["stale-state"]["after_p1"]
            ss_after_p2_cnt += result_map["stale-state"]["after_p2"]
            ss_cnt += result_map["stale-state"]["final"]

        sub_result_map[controller]["baseline-ds"] = ds_base_cnt
        sub_result_map[controller]["after-p1-ds"] = ds_after_p1_cnt
        sub_result_map[controller]["after-p2-ds"] = ds_after_p2_cnt
        sub_result_map[controller]["ds"] = ds_cnt

        sub_result_map[controller]["baseline-ss"] = ss_base_cnt
        sub_result_map[controller]["after-p1-ss"] = ss_after_p1_cnt
        sub_result_map[controller]["after-p2-ss"] = ss_after_p2_cnt
        sub_result_map[controller]["ss"] = ss_cnt

        sub_result_map[controller]["baseline-ms"] = ms_base_cnt
        sub_result_map[controller]["after-p1-ms"] = ms_after_p1_cnt
        sub_result_map[controller]["after-p2-ms"] = ms_after_p2_cnt
        sub_result_map[controller]["ms"] = ms_cnt
    return sub_result_map


def overwrite_config_json(new_config):
    shutil.copy("sieve_config.json", "sieve_config.json.bkp")
    my_config = json.load(open("sieve_config.json"))
    for key in new_config:
        my_config[key] = new_config[key]
    json.dump(my_config, open("sieve_config.json", "w"))


def recover_config_json():
    shutil.copy("sieve_config.json.bkp", "sieve_config.json")


def learn_all():
    for controller in common.controllers_to_check:
        for test_suite in common.controllers_to_check[controller]:
            docker_repo_name = get_common_config().container_registry
            cmd = "python3 sieve.py -p %s -t %s -d %s -s learn --phase=check" % (
                controller,
                test_suite,
                docker_repo_name,
            )
            os.system(cmd)


def generate_test_plan_stat():
    table = "controller\tbaseline-ds\tafter-p1-ds\tafter-p2-ds\tds\tbaseline-ss\tafter-p1-ss\tafter-p2-ss\tss\tbaseline-ms\tafter-p1-ms\tafter-p2-ms\tms\tbaseline-total\tafter-p1-total\tafter-p2-total\ttotal\n"
    short_table = (
        "controller\tintermediate-state\tstale-state\tunobserved-state\ttotal\n"
    )
    learn_all()
    sub_map = collect_spec()
    for controller in common.controllers_to_check:
        baseline_ds = sub_map[controller]["baseline-ds"]
        baseline_ss = sub_map[controller]["baseline-ss"]
        baseline_ms = sub_map[controller]["baseline-ms"]
        after_p1_ds = sub_map[controller]["after-p1-ds"]
        after_p1_ss = sub_map[controller]["after-p1-ss"]
        after_p1_ms = sub_map[controller]["after-p1-ms"]
        after_p2_ds = sub_map[controller]["after-p2-ds"]
        after_p2_ss = sub_map[controller]["after-p2-ss"]
        after_p2_ms = sub_map[controller]["after-p2-ms"]
        ds = sub_map[controller]["ds"]
        ss = sub_map[controller]["ss"]
        ms = sub_map[controller]["ms"]

        table += "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(
            controller,
            baseline_ds,
            after_p1_ds,
            after_p2_ds,
            ds,
            baseline_ss,
            after_p1_ss,
            after_p2_ss,
            ss,
            baseline_ms,
            after_p1_ms,
            after_p2_ms,
            ms,
            baseline_ds + baseline_ss + baseline_ms,
            after_p1_ds + after_p1_ss + after_p1_ms,
            after_p2_ds + after_p2_ss + after_p2_ms,
            ds + ss + ms,
        )
        short_table += "{}\t{}\t{}\t{}\t{}\n".format(
            controller,
            ds,
            ss,
            ms,
            ds + ss + ms,
        )
    print(short_table)
    open("test_plan_stats.tsv", "w").write(table)
