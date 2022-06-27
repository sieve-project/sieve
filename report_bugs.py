import json
import glob

test_result_files = glob.glob("sieve_test_results/*.json")
potential_bug_list = ""
for test_result_file in test_result_files:
    test_result = json.load(open(test_result_file))
    for controller in test_result:
        for test_case in test_result[controller]:
            for mode in test_result[controller][test_case]:
                for test_plan in test_result[controller][test_case][mode]:
                    inner_result = test_result[controller][test_case][mode][test_plan]
                    if (
                        inner_result["injection_completed"]
                        and inner_result["workload_completed"]
                        and inner_result["no_exception"]
                        and inner_result["number_errors"] > 0
                    ):
                        potential_bug_list += test_result_file + "\n"

print(
    "Please refer to the following test results for potential bugs found by Sieve\n"
    + potential_bug_list
)
