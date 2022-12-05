import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
sieve_root = os.path.dirname(os.path.dirname(os.path.dirname(current)))
sys.path.append(sieve_root)

from sieve_test_driver.test_framework import new_built_in_workload
from sieve_common.common import RUNNING, TERMINATED

test_cases = {
    "w1": new_built_in_workload()
    .cmd("kubectl apply -f examples/kapp-controller/test/1.yml")
    .wait_for_pod_status("simple-app-*", RUNNING)
    .cmd("kubectl delete app simple-app")
    .wait_for_pod_status("simple-app-*", TERMINATED)
    .cmd("kubectl apply -f examples/kapp-controller/test/1.yml")
    .wait_for_pod_status("simple-app-*", RUNNING),
}

test_cases[sys.argv[1]].run(sys.argv[2])
