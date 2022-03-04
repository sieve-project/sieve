import json
import os
from typing import List, Tuple
from sieve_common.event_delta import *
from sieve_common.common import *

from sieve_common.k8s_event import *
from sieve_analyzer.causality_graph import (
    CausalityGraph,
    CausalityVertex,
    causality_vertices_connected,
)


def convert_deltafifo_etype_to_API_etype(etype: str) -> str:
    if etype == OperatorHearTypes.ADDED:
        return APIEventTypes.ADDED
    elif etype == OperatorHearTypes.UPDATED:
        return APIEventTypes.MODIFIED
    elif etype == OperatorHearTypes.DELETED:
        return APIEventTypes.DELETED
    else:
        return APIEventTypes.MODIFIED


def event_diff_validation_check(prev_etype: str, cur_etype: str):
    if prev_etype == cur_etype and (
        prev_etype == OperatorHearTypes.ADDED or prev_etype == OperatorHearTypes.DELETED
    ):
        # this should never happen
        assert False, "There should not be consecutive Deleted | Added"
    if (
        prev_etype == OperatorHearTypes.DELETED
        and cur_etype != OperatorHearTypes.ADDED
        and cur_etype != OperatorHearTypes.UPDATED
    ):
        # this should never happen
        assert False, "Deleted must be followed with Added | Updated"
    if (
        prev_etype != EVENT_NONE_TYPE
        and prev_etype != OperatorHearTypes.DELETED
        and cur_etype == OperatorHearTypes.ADDED
    ):
        # this should never happen
        assert False, "Added must be the first or follow Deleted"


def detectable_event_diff(
    recv_event: bool,
    diff_prev_obj: Optional[Dict],
    diff_cur_obj: Optional[Dict],
    prev_etype: str,
    cur_etype: str,
    signature_counter: int,
) -> bool:
    if signature_counter > 3:
        return False
    if recv_event:
        event_diff_validation_check(prev_etype, cur_etype)
        # undetectable if the first event is not ADDED
        if prev_etype == EVENT_NONE_TYPE and cur_etype != OperatorHearTypes.ADDED:
            return False
        # undetectable if not in detectable_operator_hear_types
        if cur_etype not in detectable_operator_hear_types:
            return False
        # undetectable if nothing changed after update
        elif diff_prev_obj == diff_cur_obj and cur_etype == OperatorHearTypes.UPDATED:
            return False
        else:
            return True
    else:
        # undetectable if not in detectable_operator_write_types
        if cur_etype not in detectable_operator_write_types:
            return False
        # undetectable if nothing changed after update or patch
        elif diff_prev_obj == diff_cur_obj and (
            cur_etype == OperatorWriteTypes.UPDATE
            or cur_etype == OperatorWriteTypes.PATCH
            or cur_etype == OperatorWriteTypes.STATUS_UPDATE
            or cur_etype == OperatorWriteTypes.STATUS_PATCH
        ):
            return False
        # undetectable if status update/patch does not modify status
        elif (
            diff_prev_obj is not None
            and "status" not in diff_prev_obj
            and diff_cur_obj is not None
            and "status" not in diff_cur_obj
            and (
                cur_etype == OperatorWriteTypes.STATUS_UPDATE
                or cur_etype == OperatorWriteTypes.STATUS_PATCH
            )
        ):
            return False
        else:
            return True


def nondeterministic_key(
    test_context: TestContext, event: Union[OperatorHear, OperatorWrite]
):
    generate_name = extract_generate_name(event.obj_map)
    end_state = json.load(
        open(
            os.path.join(
                test_context.oracle_dir,
                "state.json",
            )
        )
    )
    if event.key not in end_state:
        # TODO: get rid of the heuristic
        if generate_name is not None and is_generated_random_name(
            event.name, generate_name
        ):
            return True
    elif end_state[event.key] == "SIEVE-IGNORE":
        return True
    return False


def stale_state_detectable_pass(
    test_context: TestContext,
    causality_pairs: List[Tuple[CausalityVertex, CausalityVertex]],
):
    print("Running stale state detectable pass...")
    candidate_pairs = []
    for pair in causality_pairs:
        operator_hear = pair[0].content
        operator_write = pair[1].content
        if nondeterministic_key(test_context, operator_hear) or nondeterministic_key(
            test_context, operator_write
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
            candidate_pairs.append(pair)
    print("%d -> %d edges" % (len(causality_pairs), len(candidate_pairs)))
    return candidate_pairs


def get_stale_state_baseline(causality_graph: CausalityGraph):
    operator_hear_vertices = causality_graph.operator_hear_vertices
    operator_write_vertices = causality_graph.operator_write_vertices
    candidate_pairs = []
    for operator_write_vertex in operator_write_vertices:
        for operator_hear_vertex in operator_hear_vertices:
            operator_write = operator_write_vertex.content
            operator_hear = operator_hear_vertex.content
            if not operator_write.etype == OperatorWriteTypes.DELETE:
                continue
            write_after_hear = (
                operator_write.start_timestamp > operator_hear.start_timestamp
            )

            if write_after_hear:
                pair = (operator_hear_vertex, operator_write_vertex)
                candidate_pairs.append(pair)
    return candidate_pairs


def causality_pair_filtering_pass(
    causality_pairs: List[Tuple[CausalityVertex, CausalityVertex]],
):
    print("Running optional pass: causality-filtering...")
    candidate_pairs = []
    for pair in causality_pairs:
        source = pair[0]
        sink = pair[1]
        if causality_vertices_connected(source, sink):
            candidate_pairs.append(pair)
    print("%d -> %d edges" % (len(causality_pairs), len(candidate_pairs)))
    return candidate_pairs


def reversed_effect_filtering_pass(
    causality_pairs: List[Tuple[CausalityVertex, CausalityVertex]],
    causality_graph: CausalityGraph,
):
    print("Running optional pass: reversed-effect-filtering...")
    candidate_pairs = []
    hear_key_to_vertices = causality_graph.operator_hear_key_to_vertices
    for pair in causality_pairs:
        operator_write = pair[1].content
        assert operator_write.etype == OperatorWriteTypes.DELETE
        if operator_write.error not in ALLOWED_ERROR_TYPE:
            continue
        reversed_effect = False
        if operator_write.key in hear_key_to_vertices:
            for operator_hear_vertex in hear_key_to_vertices[operator_write.key]:
                operator_hear = operator_hear_vertex.content
                if operator_hear.start_timestamp <= operator_write.end_timestamp:
                    continue
                if operator_hear.etype == OperatorHearTypes.ADDED:
                    reversed_effect = True
                if operator_hear.etype == OperatorHearTypes.UPDATED:
                    reversed_effect = True
        else:
            # if the operator_write key never appears in the operator_hear_key_map
            # it means the operator does not watch on the resource
            # so we should be cautious and keep this edge
            reversed_effect = True
        if reversed_effect:
            candidate_pairs.append(pair)
    print("%d -> %d edges" % (len(causality_pairs), len(candidate_pairs)))
    return candidate_pairs


def decide_stale_state_timing(
    source_vertex: CausalityVertex, sink_vertex: CausalityVertex
):
    assert source_vertex.is_operator_hear()
    assert sink_vertex.is_operator_write()
    assert sink_vertex.content.etype == OperatorWriteTypes.DELETE
    if source_vertex.content.slim_prev_obj_map is None:
        return "after"
    if not same_key(
        source_vertex.content.slim_prev_obj_map, source_vertex.content.slim_cur_obj_map
    ):
        return "after"
    reconcile_cnt = 0
    cur_vertex = sink_vertex
    while True:
        if len(cur_vertex.out_intra_reconciler_edges) == 1:
            next_vertex = cur_vertex.out_intra_reconciler_edges[0].sink
            if next_vertex.is_reconcile_end():
                reconcile_cnt += 1
                if reconcile_cnt == 2:
                    return "after"
            elif next_vertex.is_operator_write():
                if (
                    next_vertex.content.etype == OperatorWriteTypes.CREATE
                    and next_vertex.content.key == sink_vertex.content.key
                ):
                    if reconcile_cnt == 0:
                        print("decide timing: before")
                        return "before"
                    else:
                        print("decide timing: both")
                        return "both"
            cur_vertex = next_vertex
        elif len(sink_vertex.out_intra_reconciler_edges) == 0:
            return "after"
        else:
            assert False


def generate_stale_state_test_plan(
    test_context: TestContext,
    operator_hear: OperatorHear,
    operator_write: OperatorWrite,
    pause_timing,
):
    resource_key1 = generate_key(
        operator_hear.rtype, operator_hear.namespace, operator_hear.name
    )
    resource_key2 = generate_key(
        operator_write.rtype, operator_write.namespace, operator_write.name
    )
    condition_for_trigger1 = {}
    if operator_hear.etype == OperatorHearTypes.ADDED:
        condition_for_trigger1["conditionType"] = "onObjectCreate"
        condition_for_trigger1["resourceKey"] = resource_key1
        condition_for_trigger1["occurrence"] = operator_hear.signature_counter
    elif operator_hear.etype == OperatorHearTypes.DELETED:
        condition_for_trigger1["conditionType"] = "onObjectDelete"
        condition_for_trigger1["resourceKey"] = resource_key1
        condition_for_trigger1["occurrence"] = operator_hear.signature_counter
    else:
        condition_for_trigger1["conditionType"] = "onObjectUpdate"
        condition_for_trigger1["resourceKey"] = resource_key1
        condition_for_trigger1["prevStateDiff"] = json.dumps(
            operator_hear.slim_prev_obj_map, sort_keys=True
        )
        condition_for_trigger1["curStateDiff"] = json.dumps(
            operator_hear.slim_cur_obj_map, sort_keys=True
        )
        if (
            operator_hear.rtype
            not in test_context.controller_config.custom_resource_definitions
        ):
            condition_for_trigger1["convertStateToAPIForm"] = True
        condition_for_trigger1["occurrence"] = operator_hear.signature_counter
    return {
        "actions": [
            {
                "actionType": "pauseAPIServer",
                "apiServerName": test_context.common_config.following_api,
                "pauseScope": resource_key1,
                "trigger": {
                    "definitions": [
                        {
                            "triggerName": "trigger1",
                            "condition": condition_for_trigger1,
                            "observationPoint": {
                                "when": "afterAPIServerRecv"
                                if pause_timing == "after"
                                else "beforeAPIServerRecv",
                                "by": test_context.common_config.following_api,
                            },
                        }
                    ],
                    "expression": "trigger1",
                },
            },
            {
                "actionType": "reconnectController",
                "controllerLabel": test_context.controller_config.controller_pod_label,
                "reconnectAPIServer": test_context.common_config.following_api,
                "async": True,
                "waitBefore": 10,
                "trigger": {
                    "definitions": [
                        {
                            "triggerName": "trigger2",
                            "condition": {
                                "conditionType": "onObjectCreate",
                                "resourceKey": resource_key2,
                                "occurrence": 1,
                            },
                            "observationPoint": {
                                "when": "afterAPIServerRecv",
                                "by": test_context.common_config.leading_api,
                            },
                        }
                    ],
                    "expression": "trigger2",
                },
            },
            {
                "actionType": "resumeAPIServer",
                "apiServerName": test_context.common_config.following_api,
                "pauseScope": resource_key1,
                "trigger": {
                    "definitions": [
                        {
                            "triggerName": "trigger3",
                            "condition": {
                                "conditionType": "onTimeout",
                                "timeoutValue": 20,
                            },
                        }
                    ],
                    "expression": "trigger3",
                },
            },
        ]
    }


def state_diff_or_empty(operator_hear_or_write: Union[OperatorWrite, OperatorHear]):
    if is_creation_or_deletion(operator_hear_or_write.etype):
        return {}, {}
    else:
        return (
            operator_hear_or_write.slim_prev_obj_map,
            operator_hear_or_write.slim_cur_obj_map,
        )


def stale_state_analysis(
    causality_graph: CausalityGraph, path: str, test_context: TestContext
):
    candidate_pairs = get_stale_state_baseline(causality_graph)
    baseline_spec_number = len(candidate_pairs)
    after_p1_spec_number = -1
    after_p2_spec_number = -1
    final_spec_number = -1
    if test_context.common_config.causality_prunning_enabled:
        candidate_pairs = causality_pair_filtering_pass(candidate_pairs)
        after_p1_spec_number = len(candidate_pairs)
    if test_context.common_config.effective_updates_pruning_enabled:
        candidate_pairs = reversed_effect_filtering_pass(
            candidate_pairs, causality_graph
        )
        after_p2_spec_number = len(candidate_pairs)
    if test_context.common_config.nondeterministic_pruning_enabled:
        candidate_pairs = stale_state_detectable_pass(test_context, candidate_pairs)
    final_spec_number = len(candidate_pairs)
    i = 0
    for pair in candidate_pairs:
        source = pair[0]
        sink = pair[1]
        operator_hear = source.content
        operator_write = sink.content
        assert isinstance(operator_hear, OperatorHear)
        assert isinstance(operator_write, OperatorWrite)

        timing = decide_stale_state_timing(source, sink)

        if timing == "after":
            stale_state_test_plan = generate_stale_state_test_plan(
                test_context, operator_hear, operator_write, timing
            )
            i += 1
            file_name = os.path.join(path, "stale-state-test-plan-%s.yaml" % (str(i)))
            if test_context.common_config.persist_test_plans_enabled:
                dump_to_yaml(stale_state_test_plan, file_name)
        elif timing == "before":
            stale_state_test_plan = generate_stale_state_test_plan(
                test_context, operator_hear, operator_write, timing
            )
            i += 1
            file_name = os.path.join(path, "stale-state-test-plan-%s.yaml" % (str(i)))
            if test_context.common_config.persist_test_plans_enabled:
                dump_to_yaml(stale_state_test_plan, file_name)
        else:
            stale_state_test_plan = generate_stale_state_test_plan(
                test_context, operator_hear, operator_write, "after"
            )
            i += 1
            file_name = os.path.join(path, "stale-state-test-plan-%s.yaml" % (str(i)))
            if test_context.common_config.persist_test_plans_enabled:
                dump_to_yaml(stale_state_test_plan, file_name)

            stale_state_test_plan = generate_stale_state_test_plan(
                test_context, operator_hear, operator_write, "before"
            )
            i += 1
            file_name = os.path.join(path, "stale-state-test-plan-%s.yaml" % (str(i)))
            if test_context.common_config.persist_test_plans_enabled:
                dump_to_yaml(stale_state_test_plan, file_name)
            baseline_spec_number += 1
            after_p1_spec_number += 1
            after_p2_spec_number += 1
            final_spec_number += 1

    cprint("Generated %d stale-state test plan(s) in %s" % (i, path), bcolors.OKGREEN)
    return (
        baseline_spec_number,
        after_p1_spec_number,
        after_p2_spec_number,
        final_spec_number,
    )


def unobserved_state_detectable_pass(
    test_context: TestContext, causality_vertices: List[CausalityVertex]
):
    print("Running unobserved state detectable pass...")
    candidate_vertices = []
    for vertex in causality_vertices:
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
    print("%d -> %d receipts" % (len(causality_vertices), len(candidate_vertices)))
    return candidate_vertices


def causality_hear_filtering_pass(causality_vertices: List[CausalityVertex]):
    print("Running optional pass: causality-filtering...")
    candidate_vertices = []
    for vertex in causality_vertices:
        if len(vertex.out_inter_reconciler_edges) > 0:
            candidate_vertices.append(vertex)
    print("%d -> %d receipts" % (len(causality_vertices), len(candidate_vertices)))
    return candidate_vertices


def impact_filtering_pass(causality_vertices: List[CausalityVertex]):
    print("Running optional pass: impact-filtering...")
    candidate_vertices = []
    for vertex in causality_vertices:
        at_least_one_successful_write = False
        for out_inter_edge in vertex.out_inter_reconciler_edges:
            resulted_write = out_inter_edge.sink.content
            if resulted_write.error in ALLOWED_ERROR_TYPE:
                at_least_one_successful_write = True
        if at_least_one_successful_write:
            candidate_vertices.append(vertex)
    print("%d -> %d receipts" % (len(causality_vertices), len(candidate_vertices)))
    return candidate_vertices


def overwrite_filtering_pass(causality_vertices: List[CausalityVertex]):
    print("Running optional pass: overwrite-filtering...")
    candidate_vertices = []
    for vertex in causality_vertices:
        if len(vertex.content.cancelled_by) > 0:
            candidate_vertices.append(vertex)
    print("%d -> %d receipts" % (len(causality_vertices), len(candidate_vertices)))
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
        ]
    }


def unobserved_state_analysis(
    causality_graph: CausalityGraph, path: str, test_context: TestContext
):
    candidate_vertices = causality_graph.operator_hear_vertices
    candidate_vertices = overwrite_filtering_pass(candidate_vertices)
    baseline_spec_number = len(candidate_vertices)
    after_p1_spec_number = -1
    after_p2_spec_number = -1
    final_spec_number = -1
    if test_context.common_config.causality_prunning_enabled:
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
        file_name = os.path.join(path, "unobserved-state-test-plan-%s.yaml" % (str(i)))
        if test_context.common_config.persist_test_plans_enabled:
            dump_to_yaml(unobserved_state_test_plan, file_name)

    cprint(
        "Generated %d unobserved-state test plan(s) in %s" % (i, path), bcolors.OKGREEN
    )
    return (
        baseline_spec_number,
        after_p1_spec_number,
        after_p2_spec_number,
        final_spec_number,
    )


def intermediate_state_detectable_pass(
    test_context: TestContext, causality_vertices: List[CausalityVertex]
):
    print("Running intermediate state detectable pass...")
    candidate_vertices = []
    for vertex in causality_vertices:
        if vertex.is_operator_non_k8s_write():
            candidate_vertices.append(vertex)
        else:
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
    print("%d -> %d writes" % (len(causality_vertices), len(candidate_vertices)))
    return candidate_vertices


def effective_write_filtering_pass(causality_vertices: List[CausalityVertex]):
    print("Running optional pass:  effective-write-filtering...")
    candidate_vertices = []
    for vertex in causality_vertices:
        if vertex.is_operator_non_k8s_write():
            candidate_vertices.append(vertex)
        else:
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
    print("%d -> %d writes" % (len(causality_vertices), len(candidate_vertices)))
    return candidate_vertices


def no_error_write_filtering_pass(causality_vertices: List[CausalityVertex]):
    print("Running optional pass:  no-error-write-filtering...")
    candidate_vertices = []
    for vertex in causality_vertices:
        if vertex.is_operator_non_k8s_write():
            candidate_vertices.append(vertex)
        elif vertex.content.error in ALLOWED_ERROR_TYPE:
            candidate_vertices.append(vertex)
    print("%d -> %d writes" % (len(causality_vertices), len(candidate_vertices)))
    return candidate_vertices


def generate_intermediate_state_test_plan(
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
        ]
    }


def intermediate_state_analysis(
    causality_graph: CausalityGraph, path: str, test_context: TestContext
):
    candidate_vertices = (
        causality_graph.operator_write_vertices
        + causality_graph.operator_non_k8s_write_vertices
    )
    baseline_spec_number = len(candidate_vertices)
    after_p1_spec_number = -1
    after_p2_spec_number = -1
    final_spec_number = -1
    after_p1_spec_number = len(candidate_vertices)
    if test_context.common_config.effective_updates_pruning_enabled:
        candidate_vertices = effective_write_filtering_pass(candidate_vertices)
        candidate_vertices = no_error_write_filtering_pass(candidate_vertices)
        after_p2_spec_number = len(candidate_vertices)
    if test_context.common_config.nondeterministic_pruning_enabled:
        candidate_vertices = intermediate_state_detectable_pass(
            test_context, candidate_vertices
        )
    final_spec_number = len(candidate_vertices)
    i = 0
    for vertex in candidate_vertices:
        operator_write = vertex.content

        if isinstance(operator_write, OperatorWrite):
            intermediate_state_test_plan = generate_intermediate_state_test_plan(
                test_context, operator_write
            )
            i += 1
            file_name = os.path.join(
                path, "intermediate-state-test-plan-%s.yaml" % (str(i))
            )
            if test_context.common_config.persist_test_plans_enabled:
                dump_to_yaml(intermediate_state_test_plan, file_name)
        else:
            print("skip nk write for now")
            # assert isinstance(operator_write, OperatorNonK8sWrite)
            # # TODO: We need a better handling for non k8s event
            # intermediate_state_config["se-name"] = operator_write.fun_name
            # intermediate_state_config["se-namespace"] = "default"
            # intermediate_state_config["se-rtype"] = operator_write.recv_type
            # intermediate_state_config[
            #     "se-reconciler-type"
            # ] = operator_write.reconciler_type
            # intermediate_state_config["se-etype-previous"] = ""
            # intermediate_state_config["se-etype-current"] = NON_K8S_WRITE
            # intermediate_state_config["se-diff-previous"] = json.dumps({})
            # intermediate_state_config["se-diff-current"] = json.dumps({})
            # intermediate_state_config["se-counter"] = str(
            #     operator_write.signature_counter
            # )

    cprint(
        "Generated %d intermediate-state test plan(s) in %s" % (i, path),
        bcolors.OKGREEN,
    )
    return (
        baseline_spec_number,
        after_p1_spec_number,
        after_p2_spec_number,
        final_spec_number,
    )
