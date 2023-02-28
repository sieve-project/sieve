from evaluation_sanity_check import check, generate
import glob
import os


def check_bug_reproduction_test_plans():
    gen_configs = glob.glob(
        os.path.join(
            "sieve_learn_results/*/*/learn/*/*.yaml",
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


check_bug_reproduction_test_plans()
