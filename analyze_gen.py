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
    print("Running optional pass: delete-only-filtering ...")
    candidate_edges = []
    for edge in causality_edges:
        if edge.source.is_operator_hear() and edge.sink.is_operator_write():
            if edge.sink.content.etype == OperatorWriteTypes.DELETE:
                candidate_edges.append(edge)
    print("%d -> %d edges ..." % (len(causality_edges), len(candidate_edges)))
    return candidate_edges


def delete_then_recreate_filtering_pass(
    causality_edges: List[CausalityEdge],
    operator_hear_key_to_operator_hear_vertices: Dict[str, List[CausalityVertex]],
):
    print("Running optional pass: delete-then-recreate-filtering ...")
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
    print("%d -> %d edges ..." % (len(causality_edges), len(candidate_edges)))
    return candidate_edges


def time_travel_analysis(
    causality_graph: CausalityGraph,
    path: str,
    project: str,
    timing="after",
):
    causality_edges = causality_graph.operator_hear_operator_write_edges
    if DELETE_ONLY_FILTER_FLAG:
        candidate_edges = delete_only_filtering_pass(causality_edges)
    if DELETE_THEN_RECREATE_FLAG:
        candidate_edges = delete_then_recreate_filtering_pass(
            candidate_edges, causality_graph.operator_hear_key_to_operator_hear_vertices
        )
    yaml_map = {}
    yaml_map["project"] = project
    yaml_map["stage"] = "test"
    yaml_map["mode"] = sieve_modes.TIME_TRAVEL
    yaml_map["straggler"] = sieve_config.config["time_travel_straggler"]
    yaml_map["front-runner"] = sieve_config.config["time_travel_front_runner"]
    yaml_map["operator-pod-label"] = controllers.operator_pod_label[project]
    yaml_map["deployment-name"] = controllers.deployment_name[project]
    yaml_map["timing"] = timing
    suffix = "-b" if timing == "before" else ""
    i = 0
    for edge in candidate_edges:
        cur_operator_hear = edge.source.content
        operator_write = edge.sink.content
        assert isinstance(cur_operator_hear, OperatorHear)
        assert isinstance(operator_write, OperatorWrite)

        slim_prev_obj = cur_operator_hear.slim_prev_obj_map
        slim_cur_obj = cur_operator_hear.slim_cur_obj_map
        if slim_prev_obj is None and slim_cur_obj is None:
            continue
        if len(slim_prev_obj) == 0 and len(slim_cur_obj) == 0:
            continue

        yaml_map["ce-name"] = cur_operator_hear.name
        yaml_map["ce-namespace"] = cur_operator_hear.namespace
        yaml_map["ce-rtype"] = cur_operator_hear.rtype

        yaml_map["ce-diff-current"] = json.dumps(slim_cur_obj)
        yaml_map["ce-diff-previous"] = json.dumps(slim_prev_obj)
        yaml_map["ce-etype-current"] = cur_operator_hear.etype
        yaml_map["ce-etype-previous"] = cur_operator_hear.prev_etype

        yaml_map["se-name"] = operator_write.name
        yaml_map["se-namespace"] = operator_write.namespace
        yaml_map["se-rtype"] = operator_write.rtype
        assert operator_write.etype == OperatorWriteTypes.DELETE
        yaml_map["se-etype"] = "ADDED"

        i += 1
        yaml.dump(
            yaml_map,
            open(
                os.path.join(path, "time-travel-config-%s%s.yaml" % (str(i), suffix)),
                "w",
            ),
            sort_keys=False,
        )
    cprint("Generated %d time-travel config(s) in %s" % (i, path), bcolors.OKGREEN)


def cancellable_filtering_pass(
    causality_vertices: List[CausalityVertex], causality_graph: CausalityGraph
):
    print("Running optional pass: cancellable-filtering ...")
    candidate_vertices = []
    for vertex in causality_vertices:
        if len(vertex.content.cancelled_by) > 0:
            for operator_hear_id in vertex.content.cancelled_by:
                sink = causality_graph.get_operator_hear_with_id(operator_hear_id)
                if not causality_vertices_connected(vertex, sink):
                    candidate_vertices.append(vertex)
                    break
    print("%d -> %d vertices ..." % (len(causality_vertices), len(candidate_vertices)))
    return candidate_vertices


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
    yaml_map = {}
    yaml_map["project"] = project
    yaml_map["stage"] = "test"
    yaml_map["mode"] = sieve_modes.OBS_GAP
    yaml_map["operator-pod-label"] = controllers.operator_pod_label[project]
    i = 0
    for vertex in candidate_vertices:
        cur_operator_hear = vertex.content
        assert isinstance(cur_operator_hear, OperatorHear)

        slim_prev_obj = cur_operator_hear.slim_prev_obj_map
        slim_cur_obj = cur_operator_hear.slim_cur_obj_map
        if slim_prev_obj is None and slim_cur_obj is None:
            continue
        if len(slim_prev_obj) == 0 and len(slim_cur_obj) == 0:
            continue

        yaml_map["ce-name"] = cur_operator_hear.name
        yaml_map["ce-namespace"] = cur_operator_hear.namespace
        yaml_map["ce-rtype"] = cur_operator_hear.rtype

        yaml_map["ce-diff-current"] = json.dumps(slim_cur_obj)
        yaml_map["ce-diff-previous"] = json.dumps(slim_prev_obj)
        yaml_map["ce-etype-current"] = cur_operator_hear.etype
        yaml_map["ce-etype-previous"] = cur_operator_hear.prev_etype

        i += 1
        yaml.dump(
            yaml_map,
            open(os.path.join(path, "obs-gap-config-%s.yaml" % (str(i))), "w"),
            sort_keys=False,
        )
    cprint("Generated %d obs-gap config(s) in %s" % (i, path), bcolors.OKGREEN)


def atom_vio_analysis(
    causality_graph: CausalityGraph,
    path: str,
    project: str,
):
    operator_write_vertices = causality_graph.operator_write_vertices
    candidate_vertices = operator_write_vertices
    yaml_map = {}
    yaml_map["project"] = project
    yaml_map["stage"] = "test"
    yaml_map["mode"] = sieve_modes.ATOM_VIO
    yaml_map["front-runner"] = sieve_config.config["time_travel_front_runner"]
    yaml_map["operator-pod-label"] = controllers.operator_pod_label[project]
    yaml_map["deployment-name"] = controllers.deployment_name[project]
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

        yaml_map["se-name"] = operator_write.name
        yaml_map["se-namespace"] = operator_write.namespace
        yaml_map["se-rtype"] = operator_write.rtype
        yaml_map["se-etype"] = operator_write.etype
        yaml_map["se-diff-current"] = json.dumps(slim_cur_obj)
        yaml_map["se-diff-previous"] = json.dumps(slim_prev_obj)
        yaml_map["se-etype-previous"] = operator_write.prev_etype
        yaml_map["crash-location"] = "after"
        i += 1
        yaml.dump(
            yaml_map,
            open(os.path.join(path, "atomic-config-%s.yaml" % (str(i))), "w"),
            sort_keys=False,
        )
    cprint("Generated %d atomic config(s) in %s" % (i, path), bcolors.OKGREEN)
