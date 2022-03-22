import json
import sys
import os

result_map = json.load(open(sys.argv[1]))
print(
    "controller\tworkload\tpattern\ttest plan\tduration\thost\tworkload complated\tinjection completed\tno exception\tnumber errors"
)
for operator in result_map:
    if operator == "failed":
        continue
    for test_case in result_map[operator]:
        for mode in result_map[operator][test_case]:
            for config in result_map[operator][test_case][mode]:
                short_config = os.path.basename(config)
                duration = result_map[operator][test_case][mode][config]["duration"]
                host = result_map[operator][test_case][mode][config]["host"]
                workload_completed = result_map[operator][test_case][mode][config][
                    "workload_completed"
                ]
                injection_completed = result_map[operator][test_case][mode][config][
                    "injection_completed"
                ]
                no_exception = result_map[operator][test_case][mode][config][
                    "no_exception"
                ]
                number_errors = result_map[operator][test_case][mode][config][
                    "number_errors"
                ]
                # detected_errors = "\n".join(
                #     result_map[operator][test_case][mode][config]["detected_errors"]
                # )
                # test_config_content = result_map[operator][test_case][mode][config][
                #     "test_config_content"
                # ]
                # exception_message = result_map[operator][test_case][mode][config][
                #     "exception_message"
                # ]
                print(
                    "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}".format(
                        operator,
                        test_case,
                        mode,
                        short_config,
                        duration,
                        host,
                        workload_completed,
                        injection_completed,
                        no_exception,
                        number_errors,
                        # detected_errors,
                        # test_config_content,
                        # exception_message,
                    )
                )
