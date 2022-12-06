import glob
import os
from evaluation_sanity_check import common


def specs_to_map(specs):
    m = {}
    for spec in specs:
        spec_content = open(spec).read()
        if spec_content in m:
            m[spec_content].append(spec)
            # print(m[spec_content])
        else:
            m[spec_content] = []
            m[spec_content].append(spec)
    return m


def check_massive_testing_results(current_dir, previous_dir):
    for controller in common.controllers_to_check:
        for test in common.controllers_to_check[controller]:
            for mode in ["intermediate-state", "unobserved-state", "stale-state"]:
                cur_specs = glob.glob(
                    os.path.join(
                        current_dir,
                        controller,
                        test,
                        "generate-oracle/learn.yaml/" + mode + "/*.yaml",
                    )
                )
                pre_specs = glob.glob(
                    os.path.join(
                        previous_dir,
                        controller,
                        test,
                        "generate-oracle/learn.yaml/" + mode + "/*.yaml",
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
            "sieve_learn_results/*-controller/*/learn/learn.yaml/*/*.yaml",
        )
    )

    reprod_configs = glob.glob("bug_reproduction_test_plans/*.yaml")

    for reprod_config in reprod_configs:
        if "indirect" in reprod_config:
            continue
        found = False
        for gen_config in gen_configs:
            if open(reprod_config).read() == open(gen_config).read():
                print(reprod_config + " <= " + gen_config)
                found = True
        if not found:
            print("\033[91m" + reprod_config + " not found\033[0m")
