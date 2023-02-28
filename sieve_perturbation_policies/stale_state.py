import json
import os
from typing import List, Tuple
from sieve_common.event_delta import *
from sieve_common.common import *
from sieve_common.k8s_event import *
from sieve_analyzer.event_graph import (
    EventGraph,
    EventVertex,
    event_vertices_connected,
)
from sieve_perturbation_policies.common import (
    nondeterministic_key,
    detectable_event_diff,
)


def stale_state_detectable_pass(
    test_context: TestContext,
    event_pairs: List[Tuple[EventVertex, EventVertex]],
):
    print("Running stale state detectable pass...")
    candidate_pairs = []
    for pair in event_pairs:
        controller_hear = pair[0].content
        controller_write = pair[1].content
        if nondeterministic_key(test_context, controller_hear) or nondeterministic_key(
            test_context, controller_write
        ):
            continue
        if detectable_event_diff(
            True,
            controller_hear.slim_prev_obj_map,
            controller_hear.slim_cur_obj_map,
            controller_hear.prev_etype,
            controller_hear.etype,
            controller_hear.signature_counter,
        ):
            candidate_pairs.append(pair)
    print(".formatd -> .formatd edges".format(len(event_pairs), len(candidate_pairs)))
    return candidate_pairs


def get_stale_state_baseline(event_graph: EventGraph):
    controller_hear_vertices = event_graph.controller_hear_vertices
    controller_write_vertices = event_graph.controller_write_vertices
    candidate_pairs = []
    for controller_write_vertex in controller_write_vertices:
        for controller_hear_vertex in controller_hear_vertices:
            controller_write = controller_write_vertex.content
            controller_hear = controller_hear_vertex.content
            if not controller_write.etype == ControllerWriteTypes.DELETE:
                continue
            write_after_hear = (
                controller_write.start_timestamp > controller_hear.start_timestamp
            )

            if write_after_hear:
                pair = (controller_hear_vertex, controller_write_vertex)
                candidate_pairs.append(pair)
    return candidate_pairs


def causality_pair_filtering_pass(
    event_pairs: List[Tuple[EventVertex, EventVertex]],
):
    print("Running optional pass: causality-filtering...")
    candidate_pairs = []
    for pair in event_pairs:
        source = pair[0]
        sink = pair[1]
        if event_vertices_connected(source, sink):
            candidate_pairs.append(pair)
    print("{} -> {} edges".format(len(event_pairs), len(candidate_pairs)))
    return candidate_pairs


def reversed_effect_filtering_pass(
    event_pairs: List[Tuple[EventVertex, EventVertex]],
    event_graph: EventGraph,
):
    print("Running optional pass: reversed-effect-filtering...")
    candidate_pairs = []
    hear_key_to_vertices = event_graph.controller_hear_key_to_vertices
    for pair in event_pairs:
        controller_write = pair[1].content
        assert controller_write.etype == ControllerWriteTypes.DELETE
        if controller_write.error not in ALLOWED_ERROR_TYPE:
            continue
        reversed_effect = False
        if controller_write.key in hear_key_to_vertices:
            for controller_hear_vertex in hear_key_to_vertices[controller_write.key]:
                controller_hear = controller_hear_vertex.content
                if controller_hear.start_timestamp <= controller_write.end_timestamp:
                    continue
                if controller_hear.etype == ControllerHearTypes.ADDED:
                    reversed_effect = True
                if controller_hear.etype == ControllerHearTypes.UPDATED:
                    reversed_effect = True
        else:
            # if the controller_write key never appears in the controller_hear_key_map
            # it means the operator does not watch on the resource
            # so we should be cautious and keep this edge
            reversed_effect = True
        if reversed_effect:
            candidate_pairs.append(pair)
    print("{} -> {} edges".format(len(event_pairs), len(candidate_pairs)))
    return candidate_pairs


def decide_stale_state_timing(source_vertex: EventVertex, sink_vertex: EventVertex):
    assert source_vertex.is_controller_hear()
    assert sink_vertex.is_controller_write()
    assert sink_vertex.content.etype == ControllerWriteTypes.DELETE
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
            elif next_vertex.is_controller_write():
                if (
                    next_vertex.content.etype == ControllerWriteTypes.CREATE
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
    controller_hear: ControllerHear,
    controller_write: ControllerWrite,
    pause_timing,
):
    resource_key1 = generate_key(
        controller_hear.rtype, controller_hear.namespace, controller_hear.name
    )
    resource_key2 = generate_key(
        controller_write.rtype, controller_write.namespace, controller_write.name
    )
    condition_for_trigger1 = {}
    if controller_hear.etype == ControllerHearTypes.ADDED:
        condition_for_trigger1["conditionType"] = "onObjectCreate"
        condition_for_trigger1["resourceKey"] = resource_key1
        condition_for_trigger1["occurrence"] = controller_hear.signature_counter
    elif controller_hear.etype == ControllerHearTypes.DELETED:
        condition_for_trigger1["conditionType"] = "onObjectDelete"
        condition_for_trigger1["resourceKey"] = resource_key1
        condition_for_trigger1["occurrence"] = controller_hear.signature_counter
    else:
        condition_for_trigger1["conditionType"] = "onObjectUpdate"
        condition_for_trigger1["resourceKey"] = resource_key1
        condition_for_trigger1["prevStateDiff"] = json.dumps(
            controller_hear.slim_prev_obj_map, sort_keys=True
        )
        condition_for_trigger1["curStateDiff"] = json.dumps(
            controller_hear.slim_cur_obj_map, sort_keys=True
        )
        if (
            controller_hear.rtype
            not in test_context.controller_config.custom_resource_definitions
        ):
            condition_for_trigger1["convertStateToAPIForm"] = True
        condition_for_trigger1["occurrence"] = controller_hear.signature_counter
    return {
        "workload": test_context.test_workload,
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
        ],
    }


def stale_state_analysis(event_graph: EventGraph, path: str, test_context: TestContext):
    candidate_pairs = get_stale_state_baseline(event_graph)
    baseline_spec_number = len(candidate_pairs)
    after_p1_spec_number = -1
    after_p2_spec_number = -1
    final_spec_number = -1
    if test_context.common_config.causality_pruning_enabled:
        candidate_pairs = causality_pair_filtering_pass(candidate_pairs)
        after_p1_spec_number = len(candidate_pairs)
    if test_context.common_config.effective_updates_pruning_enabled:
        candidate_pairs = reversed_effect_filtering_pass(candidate_pairs, event_graph)
        after_p2_spec_number = len(candidate_pairs)
    if test_context.common_config.nondeterministic_pruning_enabled:
        candidate_pairs = stale_state_detectable_pass(test_context, candidate_pairs)
    final_spec_number = len(candidate_pairs)
    i = 0
    for pair in candidate_pairs:
        source = pair[0]
        sink = pair[1]
        controller_hear = source.content
        controller_write = sink.content
        assert isinstance(controller_hear, ControllerHear)
        assert isinstance(controller_write, ControllerWrite)

        timing = decide_stale_state_timing(source, sink)

        if timing == "after":
            stale_state_test_plan = generate_stale_state_test_plan(
                test_context, controller_hear, controller_write, timing
            )
            i += 1
            file_name = os.path.join(
                path, "stale-state-test-plan-{}.yaml".format(str(i))
            )
            if test_context.common_config.persist_test_plans_enabled:
                dump_to_yaml(stale_state_test_plan, file_name)
        elif timing == "before":
            stale_state_test_plan = generate_stale_state_test_plan(
                test_context, controller_hear, controller_write, timing
            )
            i += 1
            file_name = os.path.join(
                path, "stale-state-test-plan-{}.yaml".format(str(i))
            )
            if test_context.common_config.persist_test_plans_enabled:
                dump_to_yaml(stale_state_test_plan, file_name)
        else:
            stale_state_test_plan = generate_stale_state_test_plan(
                test_context, controller_hear, controller_write, "after"
            )
            i += 1
            file_name = os.path.join(
                path, "stale-state-test-plan-{}.yaml".format(str(i))
            )
            if test_context.common_config.persist_test_plans_enabled:
                dump_to_yaml(stale_state_test_plan, file_name)

            stale_state_test_plan = generate_stale_state_test_plan(
                test_context, controller_hear, controller_write, "before"
            )
            i += 1
            file_name = os.path.join(
                path, "stale-state-test-plan-{}.yaml".format(str(i))
            )
            if test_context.common_config.persist_test_plans_enabled:
                dump_to_yaml(stale_state_test_plan, file_name)
            baseline_spec_number += 1
            after_p1_spec_number += 1
            after_p2_spec_number += 1
            final_spec_number += 1

    cprint(
        "Generated {} stale-state test plan(s) in {}".format(i, path), bcolors.OKGREEN
    )
    return (
        baseline_spec_number,
        after_p1_spec_number,
        after_p2_spec_number,
        final_spec_number,
    )
