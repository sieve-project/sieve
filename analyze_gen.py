from analyze_util import *
import json
from typing import List
import yaml
import os
import controllers
import json
import sieve_config
from common import *


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
    operator_hear_key_to_operator_hear_vertices: Dict[str, List[CausalityVertex]],
):
    print("Running optional pass: delete-then-recreate-filtering...")
    # this should only be applied to time travel mode
    candidate_edges = []
    for edge in causality_edges:
        operator_write = edge.sink.content
        # time travel only cares about delete for now
        assert operator_write.etype == OperatorWriteTypes.DELETE
        keep_this_pair = False
        if operator_write.key in operator_hear_key_to_operator_hear_vertices:
            for operator_hear_vertex in operator_hear_key_to_operator_hear_vertices[
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


def decide_time_travel_timing(vertex: CausalityVertex):
    assert vertex.is_operator_write()
    assert vertex.content.etype == OperatorWriteTypes.DELETE
    reconcile_cnt = 0
    cur_vertex = vertex
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
                    and next_vertex.content.key == vertex.content.key
                ):
                    if reconcile_cnt == 0:
                        print("decide timing: before")
                        return "before"
                    else:
                        print("decide timing: both")
                        return "both"
            cur_vertex = next_vertex
        elif len(vertex.out_intra_reconciler_edges) == 0:
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
            candidate_edges, causality_graph.operator_hear_key_to_operator_hear_vertices
        )

    i = 0
    for edge in candidate_edges:
        operator_hear = edge.source.content
        operator_write = edge.sink.content
        assert isinstance(operator_hear, OperatorHear)
        assert isinstance(operator_write, OperatorWrite)

        slim_prev_obj = operator_hear.slim_prev_obj_map
        slim_cur_obj = operator_hear.slim_cur_obj_map
        if slim_prev_obj is None and slim_cur_obj is None:
            continue
        if len(slim_prev_obj) == 0 and len(slim_cur_obj) == 0:
            continue

        timing = decide_time_travel_timing(edge.sink)

        time_travel_config = time_travel_template(project)
        time_travel_config["ce-name"] = operator_hear.name
        time_travel_config["ce-namespace"] = operator_hear.namespace
        time_travel_config["ce-rtype"] = operator_hear.rtype
        time_travel_config["ce-diff-current"] = json.dumps(slim_cur_obj)
        time_travel_config["ce-diff-previous"] = json.dumps(slim_prev_obj)
        time_travel_config["ce-etype-current"] = operator_hear.etype
        time_travel_config["ce-etype-previous"] = operator_hear.prev_etype
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
        if len(vertex.content.cancelled_by) > 0:
            for operator_hear_id in vertex.content.cancelled_by:
                sink = causality_graph.get_operator_hear_with_id(operator_hear_id)
                if not causality_vertices_connected(vertex, sink):
                    candidate_vertices.append(vertex)
                    break
    print("%d -> %d vertices" % (len(causality_vertices), len(candidate_vertices)))
    return candidate_vertices


def obs_gap_template(project):
    return {
        "project": project,
        "stage": sieve_stages.TEST,
        "mode": sieve_modes.OBS_GAP,
        "operator-pod-label": controllers.operator_pod_label[project],
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

        slim_prev_obj = operator_hear.slim_prev_obj_map
        slim_cur_obj = operator_hear.slim_cur_obj_map
        if slim_prev_obj is None and slim_cur_obj is None:
            continue
        if len(slim_prev_obj) == 0 and len(slim_cur_obj) == 0:
            continue

        obs_gap_config = obs_gap_template(project)
        obs_gap_config["ce-name"] = operator_hear.name
        obs_gap_config["ce-namespace"] = operator_hear.namespace
        obs_gap_config["ce-rtype"] = operator_hear.rtype
        obs_gap_config["ce-diff-current"] = json.dumps(slim_cur_obj)
        obs_gap_config["ce-diff-previous"] = json.dumps(slim_prev_obj)
        obs_gap_config["ce-etype-current"] = operator_hear.etype
        obs_gap_config["ce-etype-previous"] = operator_hear.prev_etype

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
        assert isinstance(operator_write, OperatorWrite)

        slim_prev_obj = operator_write.slim_prev_obj_map
        slim_cur_obj = operator_write.slim_cur_obj_map
        if slim_prev_obj is None and slim_cur_obj is None:
            continue
        if (
            len(slim_prev_obj) == 0
            and len(slim_cur_obj) == 0
            and operator_write.etype == OperatorWriteTypes.UPDATE
        ):
            continue

        atom_vio_config = atom_vio_template(project)
        atom_vio_config["se-name"] = operator_write.name
        atom_vio_config["se-namespace"] = operator_write.namespace
        atom_vio_config["se-rtype"] = operator_write.rtype
        atom_vio_config["se-etype"] = operator_write.etype
        atom_vio_config["se-diff-current"] = json.dumps(slim_cur_obj)
        atom_vio_config["se-diff-previous"] = json.dumps(slim_prev_obj)
        atom_vio_config["se-etype-previous"] = operator_write.prev_etype

        i += 1
        file_name = os.path.join(path, "atom-vio-config-%s.yaml" % (str(i)))
        dump_to_yaml(atom_vio_config, file_name)

    cprint("Generated %d atom-vio config(s) in %s" % (i, path), bcolors.OKGREEN)
