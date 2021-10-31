from analyze_util import *
from analyze_event import *
import json
from typing import List
import os
import controllers
import json
import sieve_config
from common import *


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


def delete_only_filtering_pass(causality_edges: List[CausalityEdge]):
    print("Running optional pass: delete-only-filtering...")
    candidate_edges = []
    for edge in causality_edges:
        if edge.source.is_operator_hear() and edge.sink.is_operator_write():
            if edge.sink.content.etype == OperatorWriteTypes.DELETE:
                candidate_edges.append(edge)
    print("%d -> %d edges" % (len(causality_edges), len(candidate_edges)))
    return candidate_edges


def delete_then_recreate_filtering_pass(
    causality_edges: List[CausalityEdge],
    operator_hear_key_to_vertices: Dict[str, List[CausalityVertex]],
):
    print("Running optional pass: delete-then-recreate-filtering...")
    # this should only be applied to time travel mode
    candidate_edges = []
    for edge in causality_edges:
        operator_write = edge.sink.content
        # time travel only cares about delete for now
        assert operator_write.etype == OperatorWriteTypes.DELETE
        keep_this_pair = False
        if operator_write.key in operator_hear_key_to_vertices:
            for operator_hear_vertex in operator_hear_key_to_vertices[
                operator_write.key
            ]:
                operator_hear = operator_hear_vertex.content
                if operator_hear.start_timestamp <= operator_write.end_timestamp:
                    continue
                if operator_hear.etype == OperatorHearTypes.ADDED:
                    keep_this_pair = True
        else:
            # if the operator_write key never appears in the operator_hear_key_map
            # it means the operator does not watch on the resource
            # so we should be cautious and keep this edge
            keep_this_pair = True
        if keep_this_pair:
            candidate_edges.append(edge)
    print("%d -> %d edges" % (len(causality_edges), len(candidate_edges)))
    return candidate_edges


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
        "straggler": sieve_config.config["time_travel_straggler"],
        "front-runner": sieve_config.config["time_travel_front_runner"],
        "operator-pod-label": controllers.operator_pod_label[project],
        "deployment-name": controllers.deployment_name[project],
    }


def time_travel_analysis(causality_graph: CausalityGraph, path: str, project: str):
    causality_edges = causality_graph.operator_hear_operator_write_edges
    if DELETE_ONLY_FILTER_FLAG:
        candidate_edges = delete_only_filtering_pass(causality_edges)
    if DELETE_THEN_RECREATE_FLAG:
        candidate_edges = delete_then_recreate_filtering_pass(
            candidate_edges, causality_graph.operator_hear_key_to_vertices
        )

    i = 0
    for edge in candidate_edges:
        operator_hear = edge.source.content
        operator_write = edge.sink.content
        assert isinstance(operator_hear, OperatorHear)
        assert isinstance(operator_write, OperatorWrite)

        if not detectable_event_diff(
            sieve_modes.TIME_TRAVEL,
            operator_hear.slim_prev_obj_map,
            operator_hear.slim_cur_obj_map,
            operator_hear.prev_etype,
            operator_hear.etype,
            operator_hear.signature_counter,
        ):
            continue

        timing = decide_time_travel_timing(edge.source, edge.sink)

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
            dump_to_yaml(time_travel_config, file_name)
        else:
            time_travel_config["timing"] = "after"
            i += 1
            file_name = os.path.join(path, "time-travel-config-%s.yaml" % (str(i)))
            dump_to_yaml(time_travel_config, file_name)

            time_travel_config["timing"] = "before"
            i += 1
            file_name = os.path.join(path, "time-travel-config-%s.yaml" % (str(i)))
            dump_to_yaml(time_travel_config, file_name)

    cprint("Generated %d time-travel config(s) in %s" % (i, path), bcolors.OKGREEN)


def cancellable_filtering_pass(
    causality_vertices: List[CausalityVertex], causality_graph: CausalityGraph
):
    print("Running optional pass: cancellable-filtering...")
    candidate_vertices = []
    for vertex in causality_vertices:
        if (
            len(vertex.content.cancelled_by) > 0
            and len(vertex.out_inter_reconciler_edges) > 0
        ):
            candidate_vertices.append(vertex)
            # for operator_hear_id in vertex.content.cancelled_by:
            #     sink = causality_graph.get_operator_hear_with_id(operator_hear_id)
            #     if not causality_vertices_connected(vertex, sink):
            #         candidate_vertices.append(vertex)
            #         break
    print("%d -> %d vertices" % (len(causality_vertices), len(candidate_vertices)))
    return candidate_vertices


def obs_gap_template(project):
    return {
        "project": project,
        "stage": sieve_stages.TEST,
        "mode": sieve_modes.OBS_GAP,
    }


def obs_gap_analysis(
    causality_graph: CausalityGraph,
    path: str,
    project: str,
):
    operator_hear_vertices = causality_graph.operator_hear_vertices
    candidate_vertices = operator_hear_vertices
    if CANCELLABLE_FLAG:
        candidate_vertices = cancellable_filtering_pass(
            candidate_vertices, causality_graph
        )

    i = 0
    for vertex in candidate_vertices:
        operator_hear = vertex.content
        assert isinstance(operator_hear, OperatorHear)

        if not detectable_event_diff(
            sieve_modes.OBS_GAP,
            operator_hear.slim_prev_obj_map,
            operator_hear.slim_cur_obj_map,
            operator_hear.prev_etype,
            operator_hear.etype,
            operator_hear.signature_counter,
        ):
            continue

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
        dump_to_yaml(obs_gap_config, file_name)

    cprint("Generated %d obs-gap config(s) in %s" % (i, path), bcolors.OKGREEN)


def no_error_write_filtering_pass(causality_vertices: List[CausalityVertex]):
    print("Running optional pass:  no-error-write-filtering...")
    candidate_vertices = []
    for vertex in causality_vertices:
        if vertex.content.error in ALLOWED_ERROR_TYPE:
            candidate_vertices.append(vertex)
    print("%d -> %d vertices" % (len(causality_vertices), len(candidate_vertices)))
    return candidate_vertices


def atom_vio_template(project):
    return {
        "project": project,
        "stage": sieve_stages.TEST,
        "mode": sieve_modes.ATOM_VIO,
        "front-runner": sieve_config.config["time_travel_front_runner"],
        "operator-pod-label": controllers.operator_pod_label[project],
        "deployment-name": controllers.deployment_name[project],
    }


def atom_vio_analysis(
    causality_graph: CausalityGraph,
    path: str,
    project: str,
):
    operator_write_vertices = causality_graph.operator_write_vertices
    candidate_vertices = operator_write_vertices
    candidate_vertices = no_error_write_filtering_pass(candidate_vertices)

    i = 0
    for vertex in candidate_vertices:
        operator_write = vertex.content
        # TODO: Handle the case where operator_write == EVENT_NONE_TYPE
        assert isinstance(operator_write, OperatorWrite)

        if not detectable_event_diff(
            sieve_modes.ATOM_VIO,
            operator_write.slim_prev_obj_map,
            operator_write.slim_cur_obj_map,
            operator_write.prev_etype,
            operator_write.etype,
            operator_write.signature_counter,
        ):
            continue

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
        dump_to_yaml(atom_vio_config, file_name)

    cprint("Generated %d atom-vio config(s) in %s" % (i, path), bcolors.OKGREEN)
