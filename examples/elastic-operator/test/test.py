import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
sieve_root = os.path.dirname(os.path.dirname(os.path.dirname(current)))
sys.path.append(sieve_root)

from sieve_test_driver.test_framework import new_built_in_workload
from sieve_common.common import RUNNING, TERMINATED

test_cases = {
    "recreate": new_built_in_workload(100)
    .cmd("kubectl apply -f examples/elastic-operator/test/es-1.yaml")
    .wait_for_pod_status("elasticsearch-cluster-es-default-0", RUNNING)
    .wait_for_secret_existence("elasticsearch-cluster-es-elastic-user", True)
    .cmd("kubectl delete elasticsearch elasticsearch-cluster")
    .wait_for_pod_status("elasticsearch-cluster-es-default-0", TERMINATED)
    .wait_for_secret_existence("elasticsearch-cluster-es-elastic-user", False)
    .cmd("kubectl apply -f examples/elastic-operator/test/es-1.yaml")
    .wait_for_pod_status("elasticsearch-cluster-es-default-0", RUNNING)
    .wait_for_secret_existence("elasticsearch-cluster-es-elastic-user", True),
    "scaledown-scaleup": new_built_in_workload(100)
    .cmd("kubectl apply -f examples/elastic-operator/test/es-2.yaml")
    .wait_for_pod_status("elasticsearch-cluster-es-default-1", RUNNING)
    .wait_for_secret_existence("elasticsearch-cluster-es-elastic-user", True)
    .cmd(
        'kubectl patch elasticsearch elasticsearch-cluster --type=\'json\' -p=\'[{"op": "replace", "path": "/spec/nodeSets/0/count", "value": 1}]\''
    )
    .wait_for_pod_status("elasticsearch-cluster-es-default-1", TERMINATED)
    .wait_for_pvc_status(
        "elasticsearch-data-elasticsearch-cluster-es-default-1", TERMINATED
    )
    .cmd(
        'kubectl patch elasticsearch elasticsearch-cluster --type=\'json\' -p=\'[{"op": "replace", "path": "/spec/nodeSets/0/count", "value": 2}]\''
    )
    .wait_for_pod_status("elasticsearch-cluster-es-default-1", RUNNING),
}

test_cases[sys.argv[1]].run(sys.argv[2])
