import glob
import os
import controllers
import sys

sorted_operators = list(controllers.test_suites.keys())

current_dir = sys.argv[1]
previous_dir = sys.argv[2]


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


for operator in controllers.test_suites.keys():
    for test in controllers.test_suites[operator]:
        for mode in ["atomicity-violation", "observability-gap", "time-travel"]:
            cur_specs = glob.glob(
                os.path.join(
                    current_dir,
                    operator,
                    test,
                    "learn/learn-once/learn.yaml/" + mode + "/*.yaml",
                )
            )
            cur_cnt = len(cur_specs)
            pre_specs = glob.glob(
                os.path.join(
                    previous_dir,
                    operator,
                    test,
                    "learn/learn-once/learn.yaml/" + mode + "/*.yaml",
                )
            )
            pre_cnt = len(pre_specs)
            # if cur_cnt == pre_cnt:
            #     continue
            prev_map = specs_to_map(pre_specs)
            cur_map = specs_to_map(cur_specs)
            # for spec in prev_map:
            #     assert spec in cur_map
            for spec in set(cur_map.keys()).union(prev_map.keys()):
                if spec in cur_map and spec not in prev_map:
                    print("missing: ", cur_map[spec])
                elif spec in prev_map and spec not in cur_map:
                    print("redundant: ", prev_map[spec])
                elif len(cur_map[spec]) > len(prev_map[spec]):
                    print("missing diff:", cur_map[spec], prev_map[spec])
                elif len(cur_map[spec]) < len(prev_map[spec]):
                    print("redundant diff:", cur_map[spec], prev_map[spec])
