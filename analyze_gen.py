from analyze_util import *
import json
from typing import List
import yaml
import copy
import os
import controllers
import analyze_event
import json
import sieve_config
from common import sieve_modes


def delete_only_filtering_pass(causality_edges: List[CausalityEdge]):
    print("Running optional pass: delete-only-filtering ...")
    candidate_edges = []
    for edge in causality_edges:
        if edge.source.is_event() and edge.sink.is_side_effect():
            if edge.sink.content.etype == SideEffectTypes.DELETE:
                candidate_edges.append(edge)
    return candidate_edges


def delete_then_recreate_filtering_pass(
    causality_edges: List[CausalityEdge],
    event_key_to_event_vertices: Dict[str, List[CausalityVertex]],
):
    print("Running optional pass: delete-then-recreate-filtering ...")
    # this should only be applied to time travel mode
    candidate_edges = []
    for edge in causality_edges:
        side_effect = edge.sink.content
        # time travel only cares about delete for now
        assert side_effect.etype == SideEffectTypes.DELETE
        keep_this_pair = False
        if side_effect.key in event_key_to_event_vertices:
            for event_vertex in event_key_to_event_vertices[side_effect.key]:
                event = event_vertex.content
                if event.start_timestamp <= side_effect.end_timestamp:
                    continue
                if event.etype == EventTypes.ADDED:
                    keep_this_pair = True
        else:
            # if the side effect key never appears in the event_key_map
            # it means the operator does not watch on the resource
            # so we should be cautious and keep this edge
            keep_this_pair = True
        if keep_this_pair:
            candidate_edges.append(edge)
    return candidate_edges


def time_travel_analysis(
    causality_graph: CausalityGraph,
    path: str,
    project: str,
    timing="after",
):
    causality_edges = causality_graph.event_side_effect_edges
    candidate_edges = delete_only_filtering_pass(causality_edges)
    candidate_edges = delete_then_recreate_filtering_pass(
        candidate_edges, causality_graph.event_key_to_event_vertices
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
        cur_event = edge.source.content
        side_effect = edge.sink.content
        assert isinstance(cur_event, Event)
        assert isinstance(side_effect, SideEffect)

        slim_prev_obj = cur_event.slim_prev_obj_map
        slim_cur_obj = cur_event.slim_cur_obj_map
        if slim_prev_obj is None and slim_cur_obj is None:
            continue
        if len(slim_prev_obj) == 0 and len(slim_cur_obj) == 0:
            continue

        yaml_map["ce-name"] = cur_event.name
        yaml_map["ce-namespace"] = cur_event.namespace
        yaml_map["ce-rtype"] = cur_event.rtype

        yaml_map["ce-diff-current"] = json.dumps(slim_cur_obj)
        yaml_map["ce-diff-previous"] = json.dumps(slim_prev_obj)
        yaml_map["ce-etype-current"] = cur_event.etype
        yaml_map["ce-etype-previous"] = cur_event.prev_etype

        yaml_map["se-name"] = side_effect.name
        yaml_map["se-namespace"] = side_effect.namespace
        yaml_map["se-rtype"] = side_effect.rtype
        assert side_effect.etype == SideEffectTypes.DELETE
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
    print("Generated %d time-travel config(s) in %s" % (i, path))


def cancellable_filtering_pass(causality_vertices: List[CausalityVertex]):
    candidate_vertices = []
    for vertex in causality_vertices:
        if len(vertex.content.cancelled_by) > 0:
            candidate_vertices.append(vertex)
    return candidate_vertices


def obs_gap_analysis(
    causality_graph: CausalityGraph,
    path: str,
    project: str,
):
    event_vertices = causality_graph.event_vertices
    candidate_vertices = event_vertices
    candidate_vertices = cancellable_filtering_pass(candidate_vertices)
    yaml_map = {}
    yaml_map["project"] = project
    yaml_map["stage"] = "test"
    yaml_map["mode"] = sieve_modes.OBS_GAP
    yaml_map["operator-pod-label"] = controllers.operator_pod_label[project]
    i = 0
    for vertex in candidate_vertices:
        cur_event = vertex.content
        assert isinstance(cur_event, Event)

        slim_prev_obj = cur_event.slim_prev_obj_map
        slim_cur_obj = cur_event.slim_cur_obj_map
        if slim_prev_obj is None and slim_cur_obj is None:
            continue
        if len(slim_prev_obj) == 0 and len(slim_cur_obj) == 0:
            continue

        yaml_map["ce-name"] = cur_event.name
        yaml_map["ce-namespace"] = cur_event.namespace
        yaml_map["ce-rtype"] = cur_event.rtype

        yaml_map["ce-diff-current"] = json.dumps(slim_cur_obj)
        yaml_map["ce-diff-previous"] = json.dumps(slim_prev_obj)
        yaml_map["ce-etype-current"] = cur_event.etype
        yaml_map["ce-etype-previous"] = cur_event.prev_etype

        i += 1
        yaml.dump(
            yaml_map,
            open(os.path.join(path, "obs-gap-config-%s.yaml" % (str(i))), "w"),
            sort_keys=False,
        )
    print("Generated %d obs-gap config(s) in %s" % (i, path))


def atom_vio_analysis(
    causality_graph: CausalityGraph,
    path: str,
    project: str,
):
    causality_edges = causality_graph.event_side_effect_edges
    candidate_edges = causality_edges
    yaml_map = {}
    yaml_map["project"] = project
    yaml_map["stage"] = "test"
    yaml_map["mode"] = sieve_modes.ATOM_VIO
    yaml_map["front-runner"] = sieve_config.config["time_travel_front_runner"]
    yaml_map["operator-pod-label"] = controllers.operator_pod_label[project]
    yaml_map["deployment-name"] = controllers.deployment_name[project]
    i = 0
    for edge in candidate_edges:
        cur_event = edge.source.content
        side_effect = edge.sink.content
        assert isinstance(cur_event, Event)
        assert isinstance(side_effect, SideEffect)

        slim_prev_obj = cur_event.slim_prev_obj_map
        slim_cur_obj = cur_event.slim_cur_obj_map
        if slim_prev_obj is None and slim_cur_obj is None:
            continue
        if len(slim_prev_obj) == 0 and len(slim_cur_obj) == 0:
            continue

        yaml_map["ce-name"] = cur_event.name
        yaml_map["ce-namespace"] = cur_event.namespace
        yaml_map["ce-rtype"] = cur_event.rtype

        yaml_map["ce-diff-current"] = json.dumps(slim_cur_obj)
        yaml_map["ce-diff-previous"] = json.dumps(slim_prev_obj)
        yaml_map["ce-etype-current"] = cur_event.etype
        yaml_map["ce-etype-previous"] = cur_event.prev_etype

        yaml_map["se-name"] = side_effect.name
        yaml_map["se-namespace"] = side_effect.namespace
        yaml_map["se-rtype"] = side_effect.rtype
        yaml_map["se-etype"] = side_effect.etype

        # TODO: should find a way to determine crash location
        yaml_map["crash-location"] = "before"
        i += 1
        yaml.dump(
            yaml_map,
            open(os.path.join(path, "atomic-config-%s.yaml" % (str(i))), "w"),
            sort_keys=False,
        )
    print("Generated %d atomic config(s) in %s" % (i, path))
