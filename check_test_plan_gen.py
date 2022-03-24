from evaluation_sanity_check import check, generate
import sys

current_dir = "log"
previous_dir = sys.argv[1]

generate.generate_test_plan_stat()
check.check_massive_testing_results(current_dir, previous_dir)
check.check_bug_reproduction_test_plans()
