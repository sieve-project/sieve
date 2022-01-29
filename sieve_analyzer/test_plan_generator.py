import json
import os
from typing import List, Tuple
from sieve_common.default_config import sieve_config
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
    mode: str,
    diff_prev_obj: Optional[Dict],
    diff_cur_obj: Optional[Dict],
    prev_etype: str,
    cur_etype: str,
    signature_counter: int,
) -> bool:
    if signature_counter > 3:
        return False
    if mode == sieve_modes.STALE_STATE or mode == sieve_modes.UNOBSR_STATE:
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


def nondeterministic_key(project, test_name, event: Union[OperatorHear, OperatorWrite]):
    rtype = event.rtype
    name = event.name
    generate_name = extract_generate_name(event.obj_map)
    state_json_map = json.load(
        open(os.path.join("examples", project, "oracle", test_name, "state.json"))
    )
    if rtype in state_json_map:
        if name not in state_json_map[rtype]:
            # TODO: get rid of the heuristic
            if generate_name is not None and is_generated_random_name(
                name, generate_name
            ):
                return True
        elif state_json_map[rtype][name] == "SIEVE-IGNORE":
            return True
    return False


def stale_state_detectable_pass(
    project, test_name, causality_pairs: List[Tuple[CausalityVertex, CausalityVertex]]
):
    print("Running stale state detectable pass...")
    candidate_pairs = []
    for pair in causality_pairs:
        operator_hear = pair[0].content
        operator_write = pair[1].content
        if sieve_config["remove_nondeterministic_key_enabled"]:
            if nondeterministic_key(
                project,
                test_name,
                operator_hear,
            ) or nondeterministic_key(
                project,
                test_name,
                operator_write,
            ):
                continue
        if detectable_event_diff(
            sieve_modes.STALE_STATE,
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
            if sieve_config["stale_state_spec_generation_delete_only"]:
                if not operator_write.etype == OperatorWriteTypes.DELETE:
                    continue
            write_after_hear = (
                operator_write.start_timestamp > operator_hear.start_timestamp
            )
            # allowed_error = operator_write.error in ALLOWED_ERROR_TYPE

            # if write_after_hear and allowed_error:
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
                if (
                    sieve_config["update_cancels_delete_enabled"]
                    and operator_hear.etype == OperatorHearTypes.UPDATED
                ):
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


def stale_state_template(test_context: TestContext):
    return {
        "project": test_context.project,
        "stage": sieve_stages.TEST,
        "mode": sieve_modes.STALE_STATE,
        "straggler": sieve_config["stale_state_straggler"],
        "front-runner": sieve_config["stale_state_front_runner"],
        "operator-pod-label": test_context.controller_config.controller_pod_label,
        "deployment-name": test_context.controller_config.deployment_name,
    }


def stale_state_analysis(
    causality_graph: CausalityGraph, path: str, test_context: TestContext
):
    project = test_context.project
    test_name = test_context.test_name
    candidate_pairs = get_stale_state_baseline(causality_graph)
    baseline_spec_number = len(candidate_pairs)
    after_p1_spec_number = -1
    after_p2_spec_number = -1
    final_spec_number = -1
    if sieve_config["spec_generation_causal_info_pass_enabled"]:
        if sieve_config["stale_state_spec_generation_causality_pass_enabled"]:
            candidate_pairs = causality_pair_filtering_pass(candidate_pairs)
        after_p1_spec_number = len(candidate_pairs)
    if sieve_config["spec_generation_type_specific_pass_enabled"]:
        if sieve_config["stale_state_spec_generation_reversed_pass_enabled"]:
            candidate_pairs = reversed_effect_filtering_pass(
                candidate_pairs, causality_graph
            )
        after_p2_spec_number = len(candidate_pairs)
    if sieve_config["spec_generation_detectable_pass_enabled"]:
        candidate_pairs = stale_state_detectable_pass(
            project, test_name, candidate_pairs
        )
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

        stale_state_config = stale_state_template(test_context)
        stale_state_config["ce-name"] = operator_hear.name
        stale_state_config["ce-namespace"] = operator_hear.namespace
        stale_state_config["ce-rtype"] = operator_hear.rtype
        stale_state_config["ce-etype-previous"] = convert_deltafifo_etype_to_API_etype(
            operator_hear.prev_etype
        )
        stale_state_config["ce-etype-current"] = convert_deltafifo_etype_to_API_etype(
            operator_hear.etype
        )
        stale_state_config["ce-diff-previous"] = json.dumps(
            operator_hear.slim_prev_obj_map, sort_keys=True
        )
        stale_state_config["ce-diff-current"] = json.dumps(
            operator_hear.slim_cur_obj_map, sort_keys=True
        )
        stale_state_config["ce-counter"] = str(operator_hear.signature_counter)
        stale_state_config["ce-is-cr"] = str(
            operator_hear.rtype
            in test_context.controller_config.custom_resource_definitions
        )
        stale_state_config["se-name"] = operator_write.name
        stale_state_config["se-namespace"] = operator_write.namespace
        stale_state_config["se-rtype"] = operator_write.rtype
        assert operator_write.etype == OperatorWriteTypes.DELETE
        stale_state_config["se-etype"] = "ADDED"

        if timing == "after" or timing == "before":
            stale_state_config["timing"] = timing
            i += 1
            file_name = os.path.join(path, "stale-state-test-plan-%s.yaml" % (str(i)))
            if sieve_config["persist_specs_enabled"]:
                dump_to_yaml(stale_state_config, file_name)
        else:
            stale_state_config["timing"] = "after"
            i += 1
            file_name = os.path.join(path, "stale-state-test-plan-%s.yaml" % (str(i)))
            if sieve_config["persist_specs_enabled"]:
                dump_to_yaml(stale_state_config, file_name)

            stale_state_config["timing"] = "before"
            i += 1
            file_name = os.path.join(path, "stale-state-test-plan-%s.yaml" % (str(i)))
            if sieve_config["persist_specs_enabled"]:
                dump_to_yaml(stale_state_config, file_name)
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
    project, test_name, causality_vertices: List[CausalityVertex]
):
    print("Running unobserved state detectable pass...")
    candidate_vertices = []
    for vertex in causality_vertices:
        operator_hear = vertex.content
        if sieve_config["remove_nondeterministic_key_enabled"]:
            if nondeterministic_key(
                project,
                test_name,
                operator_hear,
            ):
                continue
        if detectable_event_diff(
            sieve_modes.UNOBSR_STATE,
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


def unobserved_state_template(project):
    return {
        "project": project,
        "stage": sieve_stages.TEST,
        "mode": sieve_modes.UNOBSR_STATE,
    }


def unobserved_state_analysis(
    causality_graph: CausalityGraph, path: str, test_context: TestContext
):
    project = test_context.project
    test_name = test_context.test_name
    candidate_vertices = causality_graph.operator_hear_vertices
    candidate_vertices = overwrite_filtering_pass(candidate_vertices)
    baseline_spec_number = len(candidate_vertices)
    after_p1_spec_number = -1
    after_p2_spec_number = -1
    final_spec_number = -1
    if sieve_config["spec_generation_causal_info_pass_enabled"]:
        if sieve_config["unobserved_state_spec_generation_causality_pass_enabled"]:
            candidate_vertices = causality_hear_filtering_pass(candidate_vertices)
        after_p1_spec_number = len(candidate_vertices)
        after_p2_spec_number = len(candidate_vertices)
    # if sieve_config["spec_generation_type_specific_pass_enabled"]:
    #     if sieve_config["unobserved_state_spec_generation_overwrite_pass_enabled"]:
    #         candidate_vertices = impact_filtering_pass(candidate_vertices)
    #     after_p2_spec_number = len(candidate_vertices)
    if sieve_config["spec_generation_detectable_pass_enabled"]:
        candidate_vertices = unobserved_state_detectable_pass(
            project, test_name, candidate_vertices
        )
    final_spec_number = len(candidate_vertices)
    i = 0
    for vertex in candidate_vertices:
        operator_hear = vertex.content
        assert isinstance(operator_hear, OperatorHear)

        unobserved_state_config = unobserved_state_template(project)
        unobserved_state_config["ce-name"] = operator_hear.name
        unobserved_state_config["ce-namespace"] = operator_hear.namespace
        unobserved_state_config["ce-rtype"] = operator_hear.rtype
        unobserved_state_config["ce-etype-previous"] = operator_hear.prev_etype
        unobserved_state_config["ce-etype-current"] = operator_hear.etype
        unobserved_state_config["ce-diff-previous"] = json.dumps(
            operator_hear.slim_prev_obj_map, sort_keys=True
        )
        unobserved_state_config["ce-diff-current"] = json.dumps(
            operator_hear.slim_cur_obj_map, sort_keys=True
        )
        unobserved_state_config["ce-counter"] = str(operator_hear.signature_counter)

        i += 1
        file_name = os.path.join(path, "unobserved-state-test-plan-%s.yaml" % (str(i)))
        if sieve_config["persist_specs_enabled"]:
            dump_to_yaml(unobserved_state_config, file_name)

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
    project, test_name, causality_vertices: List[CausalityVertex]
):
    print("Running intermediate state detectable pass...")
    candidate_vertices = []
    for vertex in causality_vertices:
        operator_write = vertex.content
        if sieve_config["remove_nondeterministic_key_enabled"]:
            if nondeterministic_key(
                project,
                test_name,
                operator_write,
            ):
                continue
        if detectable_event_diff(
            sieve_modes.INTERMEDIATE_STATE,
            operator_write.slim_prev_obj_map,
            operator_write.slim_cur_obj_map,
            operator_write.prev_etype,
            operator_write.etype,
            operator_write.signature_counter,
        ):
            candidate_vertices.append(vertex)
    print("%d -> %d writes" % (len(causality_vertices), len(candidate_vertices)))
    return candidate_vertices


def no_error_write_filtering_pass(causality_vertices: List[CausalityVertex]):
    print("Running optional pass:  no-error-write-filtering...")
    candidate_vertices = []
    for vertex in causality_vertices:
        if vertex.content.error in ALLOWED_ERROR_TYPE:
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


def intermediate_state_template(test_context: TestContext):
    return {
        "project": test_context.project,
        "stage": sieve_stages.TEST,
        "mode": sieve_modes.INTERMEDIATE_STATE,
        "front-runner": sieve_config["stale_state_front_runner"],
        "operator-pod-label": test_context.controller_config.controller_pod_label,
        "deployment-name": test_context.controller_config.deployment_name,
    }


def intermediate_state_analysis(
    causality_graph: CausalityGraph, path: str, test_context: TestContext
):
    project = test_context.project
    test_name = test_context.test_name
    candidate_vertices = causality_graph.operator_write_vertices
    baseline_spec_number = len(candidate_vertices)
    after_p1_spec_number = -1
    after_p2_spec_number = -1
    final_spec_number = -1
    after_p1_spec_number = len(candidate_vertices)
    if sieve_config["spec_generation_type_specific_pass_enabled"]:
        if sieve_config["intermediate_state_spec_generation_error_free_pass_enabled"]:
            candidate_vertices = no_error_write_filtering_pass(candidate_vertices)
        after_p2_spec_number = len(candidate_vertices)
    if sieve_config["spec_generation_detectable_pass_enabled"]:
        candidate_vertices = intermediate_state_detectable_pass(
            project, test_name, candidate_vertices
        )
    final_spec_number = len(candidate_vertices)
    i = 0
    for vertex in candidate_vertices:
        operator_write = vertex.content
        # TODO: Handle the case where operator_write == EVENT_NONE_TYPE
        assert isinstance(operator_write, OperatorWrite)

        intermediate_state_config = intermediate_state_template(test_context)
        intermediate_state_config["se-name"] = operator_write.name
        intermediate_state_config["se-namespace"] = operator_write.namespace
        intermediate_state_config["se-rtype"] = operator_write.rtype
        intermediate_state_config["se-reconciler-type"] = operator_write.reconciler_type
        intermediate_state_config["se-etype-previous"] = operator_write.prev_etype
        intermediate_state_config["se-etype-current"] = operator_write.etype
        intermediate_state_config["se-diff-previous"] = json.dumps(
            operator_write.slim_prev_obj_map, sort_keys=True
        )
        intermediate_state_config["se-diff-current"] = json.dumps(
            operator_write.slim_cur_obj_map, sort_keys=True
        )
        intermediate_state_config["se-counter"] = str(operator_write.signature_counter)

        i += 1
        file_name = os.path.join(
            path, "intermediate-state-test-plan-%s.yaml" % (str(i))
        )
        if sieve_config["persist_specs_enabled"]:
            dump_to_yaml(intermediate_state_config, file_name)

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
