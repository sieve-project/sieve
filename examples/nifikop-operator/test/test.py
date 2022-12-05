import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
sieve_root = os.path.dirname(os.path.dirname(os.path.dirname(current)))
sys.path.append(sieve_root)

from sieve_test_driver.test_framework import new_built_in_workload
from sieve_common.common import RUNNING, TERMINATED

test_cases = {
    "change-config": new_built_in_workload(60)
    .cmd("kubectl apply -f examples/nifikop-operator/test/nc-1.yaml")
    .wait_for_pod_status("simplenifi-1-*", RUNNING, 220)
    .wait_for_cr_condition(
        "nificluster",
        "simplenifi",
        [["metadata/finalizers", ["nificlusters.nifi.orange.com/finalizer"]]],
    )  # then wait for finializer to be present
    .cmd("kubectl apply -f examples/nifikop-operator/test/nc-config.yaml")
    .wait_for_cr_condition(
        "nificluster",
        "simplenifi",
        [["metadata/finalizers", ["nificlusters.nifi.orange.com/finalizer"]]],
    )  # then wait for finializer to be present
    .wait(30)
    .wait_for_pod_status("simplenifi-1-*", RUNNING, 120)
    .wait_for_cr_condition(
        "nificluster",
        "simplenifi",
        [["metadata/finalizers", ["nificlusters.nifi.orange.com/finalizer"]]],
    ),  # then wait for finializer to be present
    "recreate": new_built_in_workload(60)
    .cmd("kubectl apply -f examples/nifikop-operator/test/nc-1.yaml")
    .wait_for_pod_status("simplenifi-1-*", RUNNING)
    .wait_for_cr_condition(
        "nificluster",
        "simplenifi",
        [["metadata/finalizers", ["nificlusters.nifi.orange.com/finalizer"]]],
    )  # then wait for finializer to be present
    .cmd("kubectl delete nificluster simplenifi")
    .wait_for_pod_status("simplenifi-1-*", TERMINATED)
    .cmd("kubectl apply -f examples/nifikop-operator/test/nc-1.yaml")
    .wait_for_pod_status("simplenifi-1-*", RUNNING)
    .wait_for_cr_condition(
        "nificluster",
        "simplenifi",
        [["metadata/finalizers", ["nificlusters.nifi.orange.com/finalizer"]]],
    ),  # then wait for finializer to be present
    "scaledown-scaleup": new_built_in_workload(60)
    .cmd("kubectl apply -f examples/nifikop-operator/test/nc-2.yaml")
    .wait_for_pod_status("simplenifi-1-*", RUNNING)
    .wait_for_pod_status("simplenifi-2-*", RUNNING)
    # then wait for finializer to be present
    .wait_for_cr_condition(
        "nificluster",
        "simplenifi",
        [["metadata/finalizers", ["nificlusters.nifi.orange.com/finalizer"]]],
    )
    .cmd(
        'kubectl patch nificluster simplenifi --type=\'json\' -p=\'[{"op": "remove", "path": "/spec/nodes/1"}]\''
    )
    .wait_for_pod_status("simplenifi-2-*", TERMINATED)
    .cmd(
        'kubectl patch nificluster simplenifi --type=\'json\' -p=\'[{"op": "add", "path": "/spec/nodes/1", "value": {"id": 2, "nodeConfigGroup": "default_group"}}]\''
    )
    .wait_for_pod_status("simplenifi-2-*", RUNNING)
    # then wait for finializer to be present
    .wait_for_cr_condition(
        "nificluster",
        "simplenifi",
        [["metadata/finalizers", ["nificlusters.nifi.orange.com/finalizer"]]],
    ),
}

test_cases[sys.argv[1]].run(sys.argv[2])
