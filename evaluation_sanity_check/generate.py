import os
import controllers
import json
from sieve_common.default_config import sieve_config
from evaluation_sanity_check import common

total_result_map = {}


def collect_spec():
    sub_result_map = {}
    for operator in controllers.test_suites:
        if operator not in common.controllers_to_check:
            continue
        sub_result_map[operator] = {}
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
        for test in controllers.test_suites[operator]:
            result_filename = "sieve_learn_results/{}-{}.json".format(operator, test)
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

        sub_result_map[operator]["baseline-ds"] = ds_base_cnt
        sub_result_map[operator]["after-p1-ds"] = ds_after_p1_cnt
        sub_result_map[operator]["after-p2-ds"] = ds_after_p2_cnt
        sub_result_map[operator]["ds"] = ds_cnt

        sub_result_map[operator]["baseline-ss"] = ss_base_cnt
        sub_result_map[operator]["after-p1-ss"] = ss_after_p1_cnt
        sub_result_map[operator]["after-p2-ss"] = ss_after_p2_cnt
        sub_result_map[operator]["ss"] = ss_cnt

        sub_result_map[operator]["baseline-ms"] = ms_base_cnt
        sub_result_map[operator]["after-p1-ms"] = ms_after_p1_cnt
        sub_result_map[operator]["after-p2-ms"] = ms_after_p2_cnt
        sub_result_map[operator]["ms"] = ms_cnt
    return sub_result_map


def overwrite_config_json(new_config):
    os.system("cp sieve_config.json sieve_config.json.bkp")
    my_config = json.load(open("sieve_config.json"))
    for key in new_config:
        my_config[key] = new_config[key]
    json.dump(my_config, open("sieve_config.json", "w"))


def recover_config_json():
    os.system("cp sieve_config.json.bkp sieve_config.json")


def learn_all():
    for project in controllers.test_suites:
        if project not in common.controllers_to_check:
            continue
        for test_suite in controllers.test_suites[project]:
            docker_repo_name = sieve_config["docker_repo"]
            cmd = "python3 sieve.py -p %s -t %s -d %s -s learn --phase=check" % (
                project,
                test_suite,
                docker_repo_name,
            )
            os.system(cmd)


def generate_test_plan_stat():
    table = "controller\tbaseline-ds\tafter-p1-ds\tafter-p2-ds\tds\tbaseline-ss\tafter-p1-ss\tafter-p2-ss\tss\tbaseline-ms\tafter-p1-ms\tafter-p2-ms\tms\tbaseline-total\tafter-p1-total\tafter-p2-total\ttotal\n"
    learn_all()
    sub_map = collect_spec()
    for operator in controllers.test_suites:
        if operator not in common.controllers_to_check:
            continue
        baseline_ds = sub_map[operator]["baseline-ds"]
        baseline_ss = sub_map[operator]["baseline-ss"]
        baseline_ms = sub_map[operator]["baseline-ms"]
        after_p1_ds = sub_map[operator]["after-p1-ds"]
        after_p1_ss = sub_map[operator]["after-p1-ss"]
        after_p1_ms = sub_map[operator]["after-p1-ms"]
        after_p2_ds = sub_map[operator]["after-p2-ds"]
        after_p2_ss = sub_map[operator]["after-p2-ss"]
        after_p2_ms = sub_map[operator]["after-p2-ms"]
        ds = sub_map[operator]["ds"]
        ss = sub_map[operator]["ss"]
        ms = sub_map[operator]["ms"]

        table += "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(
            operator,
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
    print(table)
    open("test_plan_stats.tsv", "w").write(table)
