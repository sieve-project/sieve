import json
import os
from typing import List
from sieve_common.event_delta import *
from sieve_common.common import *
from sieve_common.k8s_event import *
from sieve_analyzer.event_graph import (
    EventGraph,
    EventVertex,
)
from sieve_perturbation_policies.common import (
    nondeterministic_key,
    detectable_event_diff,
)


def unobserved_state_detectable_pass(
    test_context: TestContext, event_vertices: List[EventVertex]
):
    print("Running unobserved state detectable pass...")
    candidate_vertices = []
    for vertex in event_vertices:
        operator_hear = vertex.content
        if nondeterministic_key(
            test_context,
            operator_hear,
        ):
            continue
        if detectable_event_diff(
            True,
            operator_hear.slim_prev_obj_map,
            operator_hear.slim_cur_obj_map,
            operator_hear.prev_etype,
            operator_hear.etype,
            operator_hear.signature_counter,
        ):
            candidate_vertices.append(vertex)
    print("{} -> {} receipts".format(len(event_vertices), len(candidate_vertices)))
    return candidate_vertices


def causality_hear_filtering_pass(event_vertices: List[EventVertex]):
    print("Running optional pass: causality-filtering...")
    candidate_vertices = []
    for vertex in event_vertices:
        if len(vertex.out_inter_reconciler_edges) > 0:
            candidate_vertices.append(vertex)
    print("{} -> {} receipts".format(len(event_vertices), len(candidate_vertices)))
    return candidate_vertices


def impact_filtering_pass(event_vertices: List[EventVertex]):
    print("Running optional pass: impact-filtering...")
    candidate_vertices = []
    for vertex in event_vertices:
        at_least_one_successful_write = False
        for out_inter_edge in vertex.out_inter_reconciler_edges:
            resulted_write = out_inter_edge.sink.content
            if resulted_write.error in ALLOWED_ERROR_TYPE:
                at_least_one_successful_write = True
        if at_least_one_successful_write:
            candidate_vertices.append(vertex)
    print("{} -> {} receipts".format(len(event_vertices), len(candidate_vertices)))
    return candidate_vertices


def overwrite_filtering_pass(event_vertices: List[EventVertex]):
    print("Running optional pass: overwrite-filtering...")
    candidate_vertices = []
    for vertex in event_vertices:
        if len(vertex.content.cancelled_by) > 0:
            candidate_vertices.append(vertex)
    print("{} -> {} receipts".format(len(event_vertices), len(candidate_vertices)))
    return candidate_vertices


def generate_unobserved_state_test_plan(
    test_context: TestContext,
    operator_hear: OperatorHear,
):
    resource_key = generate_key(
        operator_hear.rtype, operator_hear.namespace, operator_hear.name
    )
    condition_for_trigger1 = {}
    trigger_for_action2 = {
        "definitions": None,
        "expression": None,
    }
    if operator_hear.etype == OperatorHearTypes.ADDED:
        condition_for_trigger1["conditionType"] = "onObjectCreate"
        condition_for_trigger1["resourceKey"] = resource_key
        condition_for_trigger1["occurrence"] = operator_hear.signature_counter
        trigger_for_action2["definitions"] = [
            {
                "triggerName": "trigger2",
                "condition": {
                    "conditionType": "onObjectUpdate",
                    "resourceKey": resource_key,
                    "occurrence": 1,
                },
                "observationPoint": {
                    "when": "afterControllerRecv",
                    "by": "informer",
                },
            },
            {
                "triggerName": "trigger3",
                "condition": {
                    "conditionType": "onObjectDelete",
                    "resourceKey": resource_key,
                    "occurrence": 1,
                },
                "observationPoint": {
                    "when": "afterControllerRecv",
                    "by": "informer",
                },
            },
        ]
        trigger_for_action2["expression"] = "trigger2|trigger3"
    elif operator_hear.etype == OperatorHearTypes.DELETED:
        condition_for_trigger1["conditionType"] = "onObjectDelete"
        condition_for_trigger1["resourceKey"] = resource_key
        condition_for_trigger1["occurrence"] = operator_hear.signature_counter
        trigger_for_action2["definitions"] = [
            {
                "triggerName": "trigger2",
                "condition": {
                    "conditionType": "onObjectCreate",
                    "resourceKey": resource_key,
                    "occurrence": 1,
                },
                "observationPoint": {
                    "when": "afterControllerRecv",
                    "by": "informer",
                },
            },
            {
                "triggerName": "trigger3",
                "condition": {
                    "conditionType": "onObjectUpdate",
                    "resourceKey": resource_key,
                    "occurrence": 1,
                },
                "observationPoint": {
                    "when": "afterControllerRecv",
                    "by": "informer",
                },
            },
        ]
        trigger_for_action2["expression"] = "trigger2|trigger3"
    else:
        condition_for_trigger1["conditionType"] = "onObjectUpdate"
        condition_for_trigger1["resourceKey"] = resource_key
        condition_for_trigger1["prevStateDiff"] = json.dumps(
            operator_hear.slim_prev_obj_map, sort_keys=True
        )
        condition_for_trigger1["curStateDiff"] = json.dumps(
            operator_hear.slim_cur_obj_map, sort_keys=True
        )
        condition_for_trigger1["occurrence"] = operator_hear.signature_counter
        trigger_for_action2["definitions"] = [
            {
                "triggerName": "trigger2",
                "condition": {
                    "conditionType": "onAnyFieldModification",
                    "resourceKey": resource_key,
                    "prevStateDiff": json.dumps(
                        operator_hear.slim_cur_obj_map, sort_keys=True
                    ),
                    "occurrence": 1,
                },
                "observationPoint": {
                    "when": "afterControllerRecv",
                    "by": "informer",
                },
            },
            {
                "triggerName": "trigger3",
                "condition": {
                    "conditionType": "onObjectDelete",
                    "resourceKey": resource_key,
                    "occurrence": 1,
                },
                "observationPoint": {
                    "when": "afterControllerRecv",
                    "by": "informer",
                },
            },
        ]
        trigger_for_action2["expression"] = "trigger2|trigger3"
    return {
        "workload": test_context.test_workload,
        "actions": [
            {
                "actionType": "pauseController",
                "pauseAt": "beforeControllerRead",
                "pauseScope": resource_key,
                "avoidOngoingRead": True,
                "trigger": {
                    "definitions": [
                        {
                            "triggerName": "trigger1",
                            "condition": condition_for_trigger1,
                            "observationPoint": {
                                "when": "beforeControllerRecv",
                                "by": "informer",
                            },
                        }
                    ],
                    "expression": "trigger1",
                },
            },
            {
                "actionType": "resumeController",
                "pauseAt": "beforeControllerRead",
                "pauseScope": resource_key,
                "trigger": trigger_for_action2,
            },
        ],
    }


def unobserved_state_analysis(
    event_graph: EventGraph, path: str, test_context: TestContext
):
    candidate_vertices = event_graph.operator_hear_vertices
    candidate_vertices = overwrite_filtering_pass(candidate_vertices)
    baseline_spec_number = len(candidate_vertices)
    after_p1_spec_number = -1
    after_p2_spec_number = -1
    final_spec_number = -1
    if test_context.common_config.causality_pruning_enabled:
        candidate_vertices = causality_hear_filtering_pass(candidate_vertices)
        after_p1_spec_number = len(candidate_vertices)
        after_p2_spec_number = len(candidate_vertices)
    if test_context.common_config.nondeterministic_pruning_enabled:
        candidate_vertices = unobserved_state_detectable_pass(
            test_context, candidate_vertices
        )
    final_spec_number = len(candidate_vertices)
    i = 0
    for vertex in candidate_vertices:
        operator_hear = vertex.content
        assert isinstance(operator_hear, OperatorHear)

        unobserved_state_test_plan = generate_unobserved_state_test_plan(
            test_context, operator_hear
        )

        i += 1
        file_name = os.path.join(
            path, "unobserved-state-test-plan-{}.yaml".format(str(i))
        )
        if test_context.common_config.persist_test_plans_enabled:
            dump_to_yaml(unobserved_state_test_plan, file_name)

    cprint(
        "Generated {} unobserved-state test plan(s) in {}".format(i, path),
        bcolors.OKGREEN,
    )
    return (
        baseline_spec_number,
        after_p1_spec_number,
        after_p2_spec_number,
        final_spec_number,
    )
