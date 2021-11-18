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
        ds_cnt = 0
        ms_cnt = 0
        ss_cnt = 0
        ds_base_cnt = 0
        ms_base_cnt = 0
        ss_base_cnt = 0
        for test in controllers.test_suites[operator]:
            result_filename = "sieve_learn_results/{}-{}.json".format(operator, test)
            result_map = json.load(open(result_filename))
            ds_base_cnt += result_map["atomicity-violation"]["baseline"]
            ds_cnt += result_map["atomicity-violation"]["final"]
            ms_base_cnt += result_map["observability-gap"]["baseline"]
            ms_cnt += result_map["observability-gap"]["final"]
            ss_base_cnt += result_map["time-travel"]["baseline"]
            ss_cnt += result_map["time-travel"]["final"]
        sub_result_map[operator]["ds"] = ds_cnt
        sub_result_map[operator]["baseline-ds"] = ds_base_cnt
        sub_result_map[operator]["ss"] = ss_cnt
        sub_result_map[operator]["baseline-ss"] = ss_base_cnt
        sub_result_map[operator]["ms"] = ms_cnt
        sub_result_map[operator]["baseline-ms"] = ms_base_cnt
    return sub_result_map


def overwrite_config_json(new_config):
    os.system("cp sieve_config.json sieve_config.json.bkp")
    my_config = json.load(open("sieve_config.json"))
    for key in new_config:
        my_config[key] = new_config[key]
    json.dump(my_config, open("sieve_config.json", "w"))


def recover_config_json():
    os.system("cp sieve_config.json.bkp sieve_config.json")


def learn_all(config="all"):
    for project in controllers.test_suites:
        for test_suite in controllers.test_suites[project]:
            docker_repo_name = sieve_config["docker_repo"]
            if config == "detectable_only":
                overwrite_config_json(
                    {
                        "spec_generation_causal_info_pass_enabled": False,
                        "spec_generation_type_specific_pass_enabled": False,
                        "persist_specs_enabled": False,
                    }
                )
            elif config == "causality_only":
                overwrite_config_json(
                    {
                        "spec_generation_detectable_pass_enabled": False,
                        "spec_generation_type_specific_pass_enabled": False,
                        "persist_specs_enabled": False,
                    }
                )
            elif config == "type_specific_only":
                overwrite_config_json(
                    {
                        "spec_generation_detectable_pass_enabled": False,
                        "spec_generation_causal_info_pass_enabled": False,
                        "persist_specs_enabled": False,
                    }
                )
            cmd = "python3 sieve.py -p %s -t %s -d %s -s learn --phase=check_only" % (
                project,
                test_suite,
                docker_repo_name,
            )
            os.system(cmd)
            if (
                config == "detectable_only"
                or config == "type_specific_only"
                or config == "causality_only"
            ):
                recover_config_json()


if __name__ == "__main__":
    table = "controller\tds\td-ds\tc-ds\ts-ds\tbaseline-ds\tss\td-ss\tc-ss\ts-ss\tbaseline-ss\tms\td-ms\tc-ms\ts-ms\tbaseline-ms\ttotal\td-total\tc-total\ts-total\tbaseline-total\n"
    learn_all()
    sub_map = collect_spec()
    learn_all("detectable_only")
    d_sub_map = collect_spec()
    learn_all("causality_only")
    c_sub_map = collect_spec()
    learn_all("type_specific_only")
    s_sub_map = collect_spec()
    for operator in controllers.test_suites:
        ds = sub_map[operator]["ds"]
        d_ds = d_sub_map[operator]["ds"]
        c_ds = c_sub_map[operator]["ds"]
        s_ds = s_sub_map[operator]["ds"]
        baseline_ds = sub_map[operator]["baseline-ds"]
        ss = sub_map[operator]["ss"]
        d_ss = d_sub_map[operator]["ss"]
        c_ss = c_sub_map[operator]["ss"]
        s_ss = s_sub_map[operator]["ss"]
        baseline_ss = sub_map[operator]["baseline-ss"]
        ms = sub_map[operator]["ms"]
        d_ms = d_sub_map[operator]["ms"]
        c_ms = c_sub_map[operator]["ms"]
        s_ms = s_sub_map[operator]["ms"]
        baseline_ms = sub_map[operator]["baseline-ms"]
        table += "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(
            operator,
            ds,
            d_ds,
            c_ds,
            s_ds,
            baseline_ds,
            ss,
            d_ss,
            c_ss,
            s_ss,
            baseline_ss,
            ms,
            d_ms,
            c_ms,
            s_ms,
            baseline_ms,
            ds + ss + ms,
            d_ds + d_ss + d_ms,
            c_ds + c_ss + c_ms,
            s_ds + s_ss + s_ms,
            baseline_ds + baseline_ss + baseline_ms,
        )
    print(table)
    open("spec_stat_result.tsv", "w").write(table)
