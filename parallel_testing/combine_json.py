import glob
import json
import time
import os
import sys


def merge(result, patch):
    """
    Recursive function to merge two dict
    """
    for key in patch:
        if key not in result:
            result[key] = patch[key]
        else:
            if type(patch[key]) is not dict:
                print("ERROR: Duplicate config, overwriting")
                result[key] = patch[key]
            else:
                merge(result[key], patch[key])


if __name__ == "__main__":
    t = time.localtime()
    result_folder = sys.argv[1]
    controller = sys.argv[2]
    json_names = glob.glob(
        os.path.join(result_folder, "sieve_test_results/{}-*.json".format(controller))
    )
    generated_test_plans = glob.glob(
        os.path.join(
            result_folder,
            controller,
            "*",
            "learn",
            "*",
            "*-test-plan-*.yaml",
        )
    )

    result = {}
    result["failed"] = []
    for fname in json_names:
        with open(fname, "r") as in_json:
            patch = json.load(in_json)
            merge(result, patch)
    for test_plan in generated_test_plans:
        tokens = test_plan.split("/")
        workload_name = tokens[-6]
        expected_name = "{}-{}-{}.json".format(
            controller,
            workload_name,
            os.path.basename(test_plan),
        )
        # print(test_plan)
        # print(expected_name)
        found = False
        for json_name in json_names:
            if json_name.endswith(expected_name):
                found = True
        if not found:
            result["failed"].append(test_plan)

    with open(
        "test-summary-{}-{}-{}-{}-{}.json".format(
            t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min
        ),
        "w",
    ) as merged:
        json.dump(result, merged, indent=4, sort_keys=True)
