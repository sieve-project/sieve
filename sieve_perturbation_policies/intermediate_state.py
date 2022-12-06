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


def intermediate_state_detectable_pass(
    test_context: TestContext, event_vertices: List[EventVertex]
):
    print("Running intermediate state detectable pass...")
    candidate_vertices = []
    for vertex in event_vertices:
        assert vertex.is_operator_write()
        operator_write = vertex.content
        if nondeterministic_key(
            test_context,
            operator_write,
        ):
            continue
        if detectable_event_diff(
            False,
            operator_write.slim_prev_obj_map,
            operator_write.slim_cur_obj_map,
            operator_write.prev_etype,
            operator_write.etype,
            operator_write.signature_counter,
        ):
            candidate_vertices.append(vertex)
    print("{} -> {} writes".format(len(event_vertices), len(candidate_vertices)))
    return candidate_vertices


def effective_write_filtering_pass(event_vertices: List[EventVertex]):
    print("Running optional pass:  effective-write-filtering...")
    candidate_vertices = []
    for vertex in event_vertices:
        assert vertex.is_operator_write()
        if is_creation_or_deletion(vertex.content.etype):
            candidate_vertices.append(vertex)
        else:
            unmasked_prev_object, unmasked_cur_object = diff_event(
                vertex.content.prev_obj_map,
                vertex.content.obj_map,
                None,
                None,
                True,
                False,
            )
            cur_etype = vertex.content.etype
            empty_write = False
            if unmasked_prev_object == unmasked_cur_object and (
                cur_etype == OperatorWriteTypes.UPDATE
                or cur_etype == OperatorWriteTypes.PATCH
                or cur_etype == OperatorWriteTypes.STATUS_UPDATE
                or cur_etype == OperatorWriteTypes.STATUS_PATCH
            ):
                empty_write = True
            elif (
                unmasked_prev_object is not None
                and "status" not in unmasked_prev_object
                and unmasked_cur_object is not None
                and "status" not in unmasked_cur_object
                and (
                    cur_etype == OperatorWriteTypes.STATUS_UPDATE
                    or cur_etype == OperatorWriteTypes.STATUS_PATCH
                )
            ):
                empty_write = True
            if not empty_write:
                candidate_vertices.append(vertex)
    print("{} -> {} writes".format(len(event_vertices), len(candidate_vertices)))
    return candidate_vertices


def no_error_write_filtering_pass(event_vertices: List[EventVertex]):
    print("Running optional pass:  no-error-write-filtering...")
    candidate_vertices = []
    for vertex in event_vertices:
        assert vertex.is_operator_write()
        if vertex.content.error in ALLOWED_ERROR_TYPE:
            candidate_vertices.append(vertex)
    print("{} -> {} writes".format(len(event_vertices), len(candidate_vertices)))
    return candidate_vertices


def generate_intermediate_state_test_plan_for_controller_write(
    test_context: TestContext, operator_write: OperatorWrite
):
    resource_key = generate_key(
        operator_write.rtype, operator_write.namespace, operator_write.name
    )
    condition = {}
    if operator_write.etype == OperatorWriteTypes.CREATE:
        condition["conditionType"] = "onObjectCreate"
        condition["resourceKey"] = resource_key
        condition["occurrence"] = operator_write.signature_counter
    elif operator_write.etype == OperatorWriteTypes.DELETE:
        condition["conditionType"] = "onObjectDelete"
        condition["resourceKey"] = resource_key
        condition["occurrence"] = operator_write.signature_counter
    else:
        condition["conditionType"] = "onObjectUpdate"
        condition["resourceKey"] = resource_key
        condition["prevStateDiff"] = json.dumps(
            operator_write.slim_prev_obj_map, sort_keys=True
        )
        condition["curStateDiff"] = json.dumps(
            operator_write.slim_cur_obj_map, sort_keys=True
        )
        condition["occurrence"] = operator_write.signature_counter
    return {
        "workload": test_context.test_workload,
        "actions": [
            {
                "actionType": "restartController",
                "controllerLabel": test_context.controller_config.controller_pod_label,
                "trigger": {
                    "definitions": [
                        {
                            "triggerName": "trigger1",
                            "condition": condition,
                            "observationPoint": {
                                "when": "afterControllerWrite",
                                "by": operator_write.reconciler_type,
                            },
                        }
                    ],
                    "expression": "trigger1",
                },
            }
        ],
    }


def generate_intermediate_state_test_plan_for_annotated_api_invocation(
    test_context: TestContext, api_invocation: OperatorNonK8sWrite
):
    return {
        "workload": test_context.test_workload,
        "actions": [
            {
                "actionType": "restartController",
                "controllerLabel": test_context.controller_config.controller_pod_label,
                "trigger": {
                    "definitions": [
                        {
                            "triggerName": "trigger1",
                            "condition": {
                                "conditionType": "onAnnotatedAPICall",
                                "module": api_invocation.module,
                                "filePath": api_invocation.file_path,
                                "receiverType": api_invocation.recv_type,
                                "funName": api_invocation.fun_name,
                                "occurrence": api_invocation.signature_counter,
                            },
                            "observationPoint": {
                                "when": "afterAnnotatedAPICall",
                                "by": api_invocation.reconciler_type,
                            },
                        }
                    ],
                    "expression": "trigger1",
                },
            }
        ],
    }


def intermediate_state_analysis(
    event_graph: EventGraph, path: str, test_context: TestContext
):
    candidate_write_vertices = event_graph.operator_write_vertices
    candidate_annotated_api_invocation_vertices = (
        event_graph.operator_non_k8s_write_vertices
    )
    baseline_spec_number = len(candidate_write_vertices) + len(
        candidate_annotated_api_invocation_vertices
    )
    after_p1_spec_number = -1
    after_p2_spec_number = -1
    final_spec_number = -1
    after_p1_spec_number = len(candidate_write_vertices) + len(
        candidate_annotated_api_invocation_vertices
    )
    if test_context.common_config.effective_updates_pruning_enabled:
        candidate_write_vertices = effective_write_filtering_pass(
            candidate_write_vertices
        )
        candidate_write_vertices = no_error_write_filtering_pass(
            candidate_write_vertices
        )
        after_p2_spec_number = len(candidate_write_vertices) + len(
            candidate_annotated_api_invocation_vertices
        )
    if test_context.common_config.nondeterministic_pruning_enabled:
        candidate_write_vertices = intermediate_state_detectable_pass(
            test_context, candidate_write_vertices
        )
    final_spec_number = len(candidate_write_vertices) + len(
        candidate_annotated_api_invocation_vertices
    )
    i = 0
    for vertex in candidate_write_vertices:
        operator_write = vertex.content
        intermediate_state_test_plan = (
            generate_intermediate_state_test_plan_for_controller_write(
                test_context, operator_write
            )
        )
        i += 1
        file_name = os.path.join(
            path, "intermediate-state-test-plan-{}.yaml".format(str(i))
        )
        if test_context.common_config.persist_test_plans_enabled:
            dump_to_yaml(intermediate_state_test_plan, file_name)

    for vertex in candidate_annotated_api_invocation_vertices:
        annotated_api_invocation = vertex.content
        intermediate_state_test_plan = (
            generate_intermediate_state_test_plan_for_annotated_api_invocation(
                test_context, annotated_api_invocation
            )
        )
        i += 1
        file_name = os.path.join(
            path, "intermediate-state-test-plan-{}.yaml".format(str(i))
        )
        if test_context.common_config.persist_test_plans_enabled:
            dump_to_yaml(intermediate_state_test_plan, file_name)
    cprint(
        "Generated {} intermediate-state test plan(s) in {}".format(i, path),
        bcolors.OKGREEN,
    )
    return (
        baseline_spec_number,
        after_p1_spec_number,
        after_p2_spec_number,
        final_spec_number,
    )
