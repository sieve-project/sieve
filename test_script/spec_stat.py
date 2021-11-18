import glob
import os
import controllers
import json
from sieve_common.default_config import sieve_config

total_result_map = {}


def collect_spec():
    sub_result_map = {}
    for operator in controllers.test_suites:
        sub_result_map[operator] = {}
        ds_base_cnt = 0
        ms_base_cnt = 0
        ss_base_cnt = 0
        ds_after_sp_cnt = 0
        ms_after_sp_cnt = 0
        ss_after_sp_cnt = 0
        ds_after_cp_cnt = 0
        ms_after_cp_cnt = 0
        ss_after_cp_cnt = 0
        ds_cnt = 0
        ms_cnt = 0
        ss_cnt = 0
        for test in controllers.test_suites[operator]:
            result_filename = "sieve_learn_results/{}-{}.json".format(operator, test)
            result_map = json.load(open(result_filename))
            ds_base_cnt += result_map["atomicity-violation"]["baseline"]
            ds_after_sp_cnt += result_map["atomicity-violation"]["after_sp"]
            ds_after_cp_cnt += result_map["atomicity-violation"]["after_cp"]
            ds_cnt += result_map["atomicity-violation"]["final"]
            ms_base_cnt += result_map["observability-gap"]["baseline"]
            ms_after_sp_cnt += result_map["observability-gap"]["after_sp"]
            ms_after_cp_cnt += result_map["observability-gap"]["after_cp"]
            ms_cnt += result_map["observability-gap"]["final"]
            ss_base_cnt += result_map["time-travel"]["baseline"]
            ss_after_sp_cnt += result_map["time-travel"]["after_sp"]
            ss_after_cp_cnt += result_map["time-travel"]["after_cp"]
            ss_cnt += result_map["time-travel"]["final"]

        sub_result_map[operator]["baseline-ds"] = ds_base_cnt
        sub_result_map[operator]["after-sp-ds"] = ds_after_sp_cnt
        sub_result_map[operator]["after-cp-ds"] = ds_after_cp_cnt
        sub_result_map[operator]["ds"] = ds_cnt

        sub_result_map[operator]["baseline-ss"] = ss_base_cnt
        sub_result_map[operator]["after-sp-ss"] = ss_after_sp_cnt
        sub_result_map[operator]["after-cp-ss"] = ss_after_cp_cnt
        sub_result_map[operator]["ss"] = ss_cnt

        sub_result_map[operator]["baseline-ms"] = ms_base_cnt
        sub_result_map[operator]["after-sp-ms"] = ms_after_sp_cnt
        sub_result_map[operator]["after-cp-ms"] = ms_after_cp_cnt
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
        for test_suite in controllers.test_suites[project]:
            docker_repo_name = sieve_config["docker_repo"]
            overwrite_config_json(
                {
                    "persist_specs_enabled": False,
                }
            )
            cmd = "python3 sieve.py -p %s -t %s -d %s -s learn --phase=check_only" % (
                project,
                test_suite,
                docker_repo_name,
            )
            os.system(cmd)

            recover_config_json()


if __name__ == "__main__":
    table = "controller\tbaseline-ds\tafter-sp-ds\tafter-cp-ds\tds\tbaseline-ss\tafter-sp-ss\tafter-cp-ss\tss\tbaseline-ms\tafter-sp-ms\tafter-cp-ms\tms\tbaseline-total\tafter-sp-total\tafter-cp-total\ttotal\n"
    learn_all()
    sub_map = collect_spec()
    for operator in controllers.test_suites:

        baseline_ds = sub_map[operator]["baseline-ds"]
        baseline_ss = sub_map[operator]["baseline-ss"]
        baseline_ms = sub_map[operator]["baseline-ms"]
        after_sp_ds = sub_map[operator]["after-sp-ds"]
        after_sp_ss = sub_map[operator]["after-sp-ss"]
        after_sp_ms = sub_map[operator]["after-sp-ms"]
        after_cp_ds = sub_map[operator]["after-cp-ds"]
        after_cp_ss = sub_map[operator]["after-cp-ss"]
        after_cp_ms = sub_map[operator]["after-cp-ms"]
        ds = sub_map[operator]["ds"]
        ss = sub_map[operator]["ss"]
        ms = sub_map[operator]["ms"]

        table += "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(
            operator,
            baseline_ds,
            after_sp_ds,
            after_cp_ds,
            ds,
            baseline_ss,
            after_sp_ss,
            after_cp_ss,
            ss,
            baseline_ms,
            after_sp_ms,
            after_cp_ms,
            ms,
            baseline_ds + baseline_ss + baseline_ms,
            after_sp_ds + after_sp_ss + after_sp_ms,
            after_cp_ds + after_cp_ss + after_cp_ms,
            ds + ss + ms,
        )
    print(table)
    open("spec_stat_result.tsv", "w").write(table)
