import json
import sys
import os

result_map = json.load(open(sys.argv[1]))
for operator in result_map:
    for test_case in result_map[operator]:
        for mode in result_map[operator][test_case]:
            for config in result_map[operator][test_case][mode]:
                short_config = os.path.basename(config)
                duration = result_map[operator][test_case][mode][config]["duration"]
                host = result_map[operator][test_case][mode][config]["host"]
                messages = result_map[operator][test_case][mode][config]["messages"]
                ret_val = result_map[operator][test_case][mode][config]["ret_val"]
                print(
                    "{}\t{}\t{}\t{}\t{}\t{}".format(
                        operator,
                        test_case,
                        mode,
                        short_config,
                        ret_val,
                        duration,
                    )
                )
