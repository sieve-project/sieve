import glob
import os
import controllers
from evaluation_sanity_check import common

mode_compability_map = {
    "atomicity-violation": "intermediate-state",
    "observability-gap": "unobserved-state",
    "time-travel": "stale-state",
}


def specs_to_map(specs):
    m = {}
    for spec in specs:
        spec_content = open(spec).read()
        for old_mode in mode_compability_map:
            spec_content = spec_content.replace(
                old_mode, mode_compability_map[old_mode]
            )
        if spec_content in m:
            m[spec_content].append(spec)
            # print(m[spec_content])
        else:
            m[spec_content] = []
            m[spec_content].append(spec)
    return m


def check_massive_testing_results(current_dir, previous_dir):
    for operator in common.controllers_to_check:
        for test in controllers.test_suites[operator]:
            for mode in ["atomicity-violation", "observability-gap", "time-travel"]:
                cur_specs = glob.glob(
                    os.path.join(
                        current_dir,
                        operator,
                        test,
                        "learn/learn-once/learn.yaml/"
                        + mode_compability_map[mode]
                        + "/*.yaml",
                    )
                )
                pre_specs = glob.glob(
                    os.path.join(
                        previous_dir,
                        operator,
                        test,
                        "learn/learn-once/learn.yaml/" + mode + "/*.yaml",
                    )
                )
                prev_map = specs_to_map(pre_specs)
                cur_map = specs_to_map(cur_specs)
                for spec in set(cur_map.keys()).union(prev_map.keys()):
                    if spec in cur_map and spec not in prev_map:
                        print("missing: ", cur_map[spec])
                    elif spec in prev_map and spec not in cur_map:
                        print("redundant: ", prev_map[spec])
                    elif len(cur_map[spec]) > len(prev_map[spec]):
                        print("missing diff:", cur_map[spec], prev_map[spec])
                    elif len(cur_map[spec]) < len(prev_map[spec]):
                        print("redundant diff:", cur_map[spec], prev_map[spec])


def check_bug_reproduction_test_plans():
    gen_configs = glob.glob(
        os.path.join(
            "log/*-operator/*/learn/learn-once/learn.yaml/*/*.yaml",
        )
    )

    reprod_configs = glob.glob("bug_reproduction_test_plans/*.yaml")

    for reprod_config in reprod_configs:
        found = False
        for gen_config in gen_configs:
            if open(reprod_config).read() == open(gen_config).read():
                print(reprod_config + " <= " + gen_config)
                found = True
        if not found:
            print("\033[91m" + reprod_config + " not found\033[0m")
