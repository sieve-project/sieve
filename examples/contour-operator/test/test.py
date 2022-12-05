import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
sieve_root = os.path.dirname(os.path.dirname(os.path.dirname(current)))
sys.path.append(sieve_root)

from sieve_test_driver.test_framework import new_built_in_workload
from sieve_common.common import TERMINATED

test_cases = {
    "recreate": new_built_in_workload(100)
    .cmd("kubectl apply -f examples/contour-operator/test/contour.yaml")
    .wait_for_pod_number("contour-", 3)
    .cmd("kubectl delete contour contour-sample")
    .wait_for_pod_status("envoy-*", TERMINATED)
    .cmd("kubectl apply -f examples/contour-operator/test/contour.yaml")
    .wait_for_pod_number("contour-", 3)
}

test_cases[sys.argv[1]].run(sys.argv[2])
