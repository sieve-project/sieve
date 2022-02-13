from evaluation_sanity_check import check, generate
import sys
import os

# current_dir = "log"
# previous_dir = sys.argv[1]

# os.system("rm -rf %s" % current_dir)
# os.system("cp -r %s %s" % (previous_dir, current_dir))

generate.generate_test_plan_stat()
# check.check_massive_testing_results(current_dir, previous_dir)
check.check_bug_reproduction_test_plans()
