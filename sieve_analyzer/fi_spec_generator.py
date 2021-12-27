import json
import os
from typing import List, Tuple

import controllers
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
    if prev_etype == OperatorHearTypes.DELETED and cur_etype != OperatorHearTypes.ADDED:
        # this should never happen
        assert False, "Deleted must be followed with Added"
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
    if mode == sieve_modes.TIME_TRAVEL or mode == sieve_modes.OBS_GAP:
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


def time_travel_detectable_pass(
    causality_pairs: List[Tuple[CausalityVertex, CausalityVertex]]
):
    print("Running time travel detectable pass...")
    candidate_pairs = []
    for pair in causality_pairs:
        operator_hear = pair[0].content
        if detectable_event_diff(
            sieve_modes.TIME_TRAVEL,
            operator_hear.slim_prev_obj_map,
            operator_hear.slim_cur_obj_map,
            operator_hear.prev_etype,
            operator_hear.etype,
            operator_hear.signature_counter,
        ):
            candidate_pairs.append(pair)
    print("%d -> %d edges" % (len(causality_pairs), len(candidate_pairs)))
    return candidate_pairs


def get_time_travel_baseline(causality_graph: CausalityGraph):
    operator_hear_vertices = causality_graph.operator_hear_vertices
    operator_write_vertices = causality_graph.operator_write_vertices
    candidate_pairs = []
    for operator_write_vertex in operator_write_vertices:
        for operator_hear_vertex in operator_hear_vertices:
            operator_write = operator_write_vertex.content
            operator_hear = operator_hear_vertex.content
            if sieve_config["time_travel_spec_generation_delete_only"]:
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
        else:
            # if the operator_write key never appears in the operator_hear_key_map
            # it means the operator does not watch on the resource
            # so we should be cautious and keep this edge
            reversed_effect = True
        if reversed_effect:
            candidate_pairs.append(pair)
    print("%d -> %d edges" % (len(causality_pairs), len(candidate_pairs)))
    return candidate_pairs


def decide_time_travel_timing(
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


def time_travel_template(project):
    return {
        "project": project,
        "stage": sieve_stages.TEST,
        "mode": sieve_modes.TIME_TRAVEL,
        "straggler": sieve_config["time_travel_straggler"],
        "front-runner": sieve_config["time_travel_front_runner"],
        "operator-pod-label": controllers.operator_pod_label[project],
        "deployment-name": controllers.deployment_name[project],
    }


def time_travel_analysis(
    causality_graph: CausalityGraph, path: str, test_context: TestContext
):
    project = test_context.project
    candidate_pairs = get_time_travel_baseline(causality_graph)
    baseline_spec_number = len(candidate_pairs)
    after_p1_spec_number = -1
    after_p2_spec_number = -1
    final_spec_number = -1
    if sieve_config["spec_generation_causal_info_pass_enabled"]:
        if sieve_config["time_travel_spec_generation_causality_pass_enabled"]:
            candidate_pairs = causality_pair_filtering_pass(candidate_pairs)
        after_p1_spec_number = len(candidate_pairs)
    if sieve_config["spec_generation_type_specific_pass_enabled"]:
        if sieve_config["time_travel_spec_generation_reversed_pass_enabled"]:
            candidate_pairs = reversed_effect_filtering_pass(
                candidate_pairs, causality_graph
            )
        after_p2_spec_number = len(candidate_pairs)
    if sieve_config["spec_generation_detectable_pass_enabled"]:
        candidate_pairs = time_travel_detectable_pass(candidate_pairs)
    final_spec_number = len(candidate_pairs)
    i = 0
    for pair in candidate_pairs:
        source = pair[0]
        sink = pair[1]
        operator_hear = source.content
        operator_write = sink.content
        assert isinstance(operator_hear, OperatorHear)
        assert isinstance(operator_write, OperatorWrite)

        timing = decide_time_travel_timing(source, sink)

        time_travel_config = time_travel_template(project)
        time_travel_config["ce-name"] = operator_hear.name
        time_travel_config["ce-namespace"] = operator_hear.namespace
        time_travel_config["ce-rtype"] = operator_hear.rtype
        time_travel_config["ce-etype-previous"] = convert_deltafifo_etype_to_API_etype(
            operator_hear.prev_etype
        )
        time_travel_config["ce-etype-current"] = convert_deltafifo_etype_to_API_etype(
            operator_hear.etype
        )
        time_travel_config["ce-diff-previous"] = json.dumps(
            operator_hear.slim_prev_obj_map, sort_keys=True
        )
        time_travel_config["ce-diff-current"] = json.dumps(
            operator_hear.slim_cur_obj_map, sort_keys=True
        )
        time_travel_config["ce-counter"] = str(operator_hear.signature_counter)
        time_travel_config["ce-is-cr"] = str(
            operator_hear.rtype in controllers.CRDs[project]
        )
        time_travel_config["se-name"] = operator_write.name
        time_travel_config["se-namespace"] = operator_write.namespace
        time_travel_config["se-rtype"] = operator_write.rtype
        assert operator_write.etype == OperatorWriteTypes.DELETE
        time_travel_config["se-etype"] = "ADDED"

        if timing == "after" or timing == "before":
            time_travel_config["timing"] = timing
            i += 1
            file_name = os.path.join(path, "time-travel-config-%s.yaml" % (str(i)))
            if sieve_config["persist_specs_enabled"]:
                dump_to_yaml(time_travel_config, file_name)
        else:
            time_travel_config["timing"] = "after"
            i += 1
            file_name = os.path.join(path, "time-travel-config-%s.yaml" % (str(i)))
            if sieve_config["persist_specs_enabled"]:
                dump_to_yaml(time_travel_config, file_name)

            time_travel_config["timing"] = "before"
            i += 1
            file_name = os.path.join(path, "time-travel-config-%s.yaml" % (str(i)))
            if sieve_config["persist_specs_enabled"]:
                dump_to_yaml(time_travel_config, file_name)
            baseline_spec_number += 1
            after_p1_spec_number += 1
            after_p2_spec_number += 1
            final_spec_number += 1

    cprint("Generated %d time-travel config(s) in %s" % (i, path), bcolors.OKGREEN)
    return (
        baseline_spec_number,
        after_p1_spec_number,
        after_p2_spec_number,
        final_spec_number,
    )


def obs_gap_detectable_pass(causality_vertices: List[CausalityVertex]):
    print("Running obs gap detectable pass...")
    candidate_vertices = []
    for vertex in causality_vertices:
        operator_hear = vertex.content
        if detectable_event_diff(
            sieve_modes.OBS_GAP,
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


def obs_gap_template(project):
    return {
        "project": project,
        "stage": sieve_stages.TEST,
        "mode": sieve_modes.OBS_GAP,
    }


def obs_gap_analysis(
    causality_graph: CausalityGraph, path: str, test_context: TestContext
):
    project = test_context.project
    candidate_vertices = causality_graph.operator_hear_vertices
    candidate_vertices = overwrite_filtering_pass(candidate_vertices)
    baseline_spec_number = len(candidate_vertices)
    after_p1_spec_number = -1
    after_p2_spec_number = -1
    final_spec_number = -1
    if sieve_config["spec_generation_causal_info_pass_enabled"]:
        if sieve_config["obs_gap_spec_generation_causality_pass_enabled"]:
            candidate_vertices = causality_hear_filtering_pass(candidate_vertices)
        after_p1_spec_number = len(candidate_vertices)
        after_p2_spec_number = len(candidate_vertices)
    # if sieve_config["spec_generation_type_specific_pass_enabled"]:
    #     if sieve_config["obs_gap_spec_generation_overwrite_pass_enabled"]:
    #         candidate_vertices = impact_filtering_pass(candidate_vertices)
    #     after_p2_spec_number = len(candidate_vertices)
    if sieve_config["spec_generation_detectable_pass_enabled"]:
        candidate_vertices = obs_gap_detectable_pass(candidate_vertices)
    final_spec_number = len(candidate_vertices)
    i = 0
    for vertex in candidate_vertices:
        operator_hear = vertex.content
        assert isinstance(operator_hear, OperatorHear)

        obs_gap_config = obs_gap_template(project)
        obs_gap_config["ce-name"] = operator_hear.name
        obs_gap_config["ce-namespace"] = operator_hear.namespace
        obs_gap_config["ce-rtype"] = operator_hear.rtype
        obs_gap_config["ce-etype-previous"] = operator_hear.prev_etype
        obs_gap_config["ce-etype-current"] = operator_hear.etype
        obs_gap_config["ce-diff-previous"] = json.dumps(
            operator_hear.slim_prev_obj_map, sort_keys=True
        )
        obs_gap_config["ce-diff-current"] = json.dumps(
            operator_hear.slim_cur_obj_map, sort_keys=True
        )
        obs_gap_config["ce-counter"] = str(operator_hear.signature_counter)

        i += 1
        file_name = os.path.join(path, "obs-gap-config-%s.yaml" % (str(i)))
        if sieve_config["persist_specs_enabled"]:
            dump_to_yaml(obs_gap_config, file_name)

    cprint("Generated %d obs-gap config(s) in %s" % (i, path), bcolors.OKGREEN)
    return (
        baseline_spec_number,
        after_p1_spec_number,
        after_p2_spec_number,
        final_spec_number,
    )


def atom_vio_detectable_pass(causality_vertices: List[CausalityVertex]):
    print("Running atom vio detectable pass...")
    candidate_vertices = []
    for vertex in causality_vertices:
        operator_write = vertex.content
        if detectable_event_diff(
            sieve_modes.ATOM_VIO,
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


def atom_vio_template(project):
    return {
        "project": project,
        "stage": sieve_stages.TEST,
        "mode": sieve_modes.ATOM_VIO,
        "front-runner": sieve_config["time_travel_front_runner"],
        "operator-pod-label": controllers.operator_pod_label[project],
        "deployment-name": controllers.deployment_name[project],
    }


def atom_vio_analysis(
    causality_graph: CausalityGraph, path: str, test_context: TestContext
):
    project = test_context.project
    candidate_vertices = causality_graph.operator_write_vertices
    baseline_spec_number = len(candidate_vertices)
    after_p1_spec_number = -1
    after_p2_spec_number = -1
    final_spec_number = -1
    after_p1_spec_number = len(candidate_vertices)
    if sieve_config["spec_generation_type_specific_pass_enabled"]:
        if sieve_config["atom_vio_spec_generation_error_free_pass_enabled"]:
            candidate_vertices = no_error_write_filtering_pass(candidate_vertices)
        after_p2_spec_number = len(candidate_vertices)
    if sieve_config["spec_generation_detectable_pass_enabled"]:
        candidate_vertices = atom_vio_detectable_pass(candidate_vertices)
    final_spec_number = len(candidate_vertices)
    i = 0
    for vertex in candidate_vertices:
        operator_write = vertex.content
        # TODO: Handle the case where operator_write == EVENT_NONE_TYPE
        assert isinstance(operator_write, OperatorWrite)

        atom_vio_config = atom_vio_template(project)
        atom_vio_config["se-name"] = operator_write.name
        atom_vio_config["se-namespace"] = operator_write.namespace
        atom_vio_config["se-rtype"] = operator_write.rtype
        atom_vio_config["se-etype-previous"] = operator_write.prev_etype
        atom_vio_config["se-etype-current"] = operator_write.etype
        atom_vio_config["se-diff-previous"] = json.dumps(
            operator_write.slim_prev_obj_map, sort_keys=True
        )
        atom_vio_config["se-diff-current"] = json.dumps(
            operator_write.slim_cur_obj_map, sort_keys=True
        )
        atom_vio_config["se-counter"] = str(operator_write.signature_counter)

        i += 1
        file_name = os.path.join(path, "atom-vio-config-%s.yaml" % (str(i)))
        if sieve_config["persist_specs_enabled"]:
            dump_to_yaml(atom_vio_config, file_name)

    cprint("Generated %d atom-vio config(s) in %s" % (i, path), bcolors.OKGREEN)
    return (
        baseline_spec_number,
        after_p1_spec_number,
        after_p2_spec_number,
        final_spec_number,
    )
