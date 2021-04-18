import json
import yaml
import copy
import sys
import os
import shutil
import kubernetes
import controllers
import common
import oracle
import analyze_event


def parse_events(path):
    # { event id -> event }
    event_id_map = {}
    # { event key -> [events belonging to the key] }
    # we need this map to later find the previous event for each crucial event
    event_key_map = {}
    event_list = []
    lines = open(path).readlines()
    for i in range(len(lines)):
        line = lines[i]
        if common.SONAR_EVENT_MARK in line:
            event = common.parse_event(line)
            event.set_start_timestamp(i)
            event_id_map[event.id] = event
        elif common.SONAR_EVENT_APPLIED_MARK in line:
            event_id_only = common.parse_event_id_only(line)
            event_id_map[event_id_only.id].set_end_timestamp(i)
    for i in range(len(lines)):
        line = lines[i]
        if common.SONAR_EVENT_MARK in line:
            event = common.parse_event(line)
            if event.key not in event_key_map:
                event_key_map[event.key] = []
            event_key_map[event.key].append(event_id_map[event.id])
            event_list.append(event_id_map[event.id])
    return event_list, event_key_map


def parse_side_effects(path):
    # TODO: we need to consider the mulit-controller situation
    side_effect_list = []
    read_types_this_reconcile = set()
    read_keys_this_reconcile = set()
    prev_reconcile_start_timestamp = -1
    cur_reconcile_start_timestamp = -1
    lines = open(path).readlines()
    for i in range(len(lines)):
        line = lines[i]
        if common.SONAR_SIDE_EFFECT_MARK in line:
            # if we have not met any reconcile yet, skip the side effect since it is not caused by reconcile
            # though it should not happen at all
            if cur_reconcile_start_timestamp == -1:
                continue
            side_effect = common.parse_side_effect(line)
            # do deepcopy here to ensure the later changes to the two sets
            # will not affect this side effect
            side_effect.set_read_keys(copy.deepcopy(read_keys_this_reconcile))
            side_effect.set_read_types(
                copy.deepcopy(read_types_this_reconcile))
            side_effect.set_end_timestamp(i)
            # if the side effect happens in the first reconcile
            # the range should be [cur_reconcile_start_timestamp, side_effect_end_timestamp]
            if prev_reconcile_start_timestamp == -1:
                side_effect.set_in_first_reconcile(True)
                side_effect.set_range(cur_reconcile_start_timestamp, i)
            # otherwise, it should be [prev_reconcile_start_timestamp, side_effect_end_timestamp]
            else:
                side_effect.set_range(prev_reconcile_start_timestamp, i)
            side_effect_list.append(side_effect)
        elif common.SONAR_CACHE_READ_MARK in line:
            cache_read = common.parse_cache_read(line)
            if cache_read.etype == "Get":
                read_keys_this_reconcile.add(cache_read.key)
            else:
                read_types_this_reconcile.add(cache_read.rtype)
        elif common.SONAR_START_RECONCILE_MARK in line:
            prev_reconcile_start_timestamp = cur_reconcile_start_timestamp
            cur_reconcile_start_timestamp = i
            # clear the read keys and types set for the new reconcile
            read_keys_this_reconcile = set()
            read_types_this_reconcile = set()
    return side_effect_list


def base_pass(event_list, side_effect_list):
    event_effect_pairs = []
    for side_effect in side_effect_list:
        if side_effect.etype not in common.INTERESTING_SIDE_EFFECT_TYPE:
            continue
        for event in event_list:
            if side_effect.range_overlap(event):
                event_effect_pairs.append([event, side_effect])
    return event_effect_pairs


def write_read_overlap_filtering_pass(event_effect_pairs):
    reduced_event_effect_pairs = []
    for pair in event_effect_pairs:
        event = pair[0]
        side_effect = pair[1]
        if side_effect.interest_overlap(event):
            reduced_event_effect_pairs.append(pair)
    return reduced_event_effect_pairs


def error_msg_filtering_pass(event_effect_pairs):
    reduced_event_effect_pairs = []
    for pair in event_effect_pairs:
        side_effect = pair[1]
        if side_effect.error not in common.FILTERED_ERROR_TYPE:
            reduced_event_effect_pairs.append(pair)
    return reduced_event_effect_pairs


def pipelined_passes(event_effect_pairs):
    reduced_event_effect_pairs = event_effect_pairs
    if common.WRITE_READ_FILTER_FLAG:
        reduced_event_effect_pairs = write_read_overlap_filtering_pass(
            reduced_event_effect_pairs)
    if common.ERROR_MSG_FILTER_FLAG:
        reduced_event_effect_pairs = error_msg_filtering_pass(
            reduced_event_effect_pairs)
    return reduced_event_effect_pairs


def generate_event_effect_pairs(path):
    event_list, event_key_map = parse_events(path)
    side_effect_list = parse_side_effects(path)
    event_effect_pairs = base_pass(event_list, side_effect_list)
    reduced_event_effect_pairs = pipelined_passes(event_effect_pairs)
    return reduced_event_effect_pairs, event_key_map


def generate_triggering_points(event_map, event_effect_pairs):
    triggering_points = []
    for pair in event_effect_pairs:
        event = pair[0]
        side_effect = pair[1]
        prev_event, cur_event = analyze_event.find_previous_event(
            event, event_map)
        triggering_point = {"name": cur_event.name,
                            "namespace": cur_event.namespace,
                            "rtype": cur_event.rtype,
                            "effect": side_effect.to_dict()}
        if prev_event is None:
            triggering_point["ttype"] = "todo"
        else:
            slim_prev_obj, slim_cur_obj = analyze_event.diff_events(
                prev_event, cur_event)
            triggering_point["ttype"] = "event-delta"
            triggering_point["prevEvent"] = slim_prev_obj
            triggering_point["curEvent"] = slim_cur_obj
            triggering_point["prevEventType"] = prev_event.etype
            triggering_point["curEventType"] = cur_event.etype
        triggering_points.append(triggering_point)
    return triggering_points


def time_travel_description(yaml_map):
    return "Pause %s after it processes a %s event E. "\
        "E should match the pattern %s and the events before E should match %s. "\
        "And restart the controller %s after %s processes a %s %s event." % (
            yaml_map["straggler"], "/".join([yaml_map["ce-namespace"],
                                             yaml_map["ce-rtype"], yaml_map["ce-name"]]),
            yaml_map["ce-diff-current"], yaml_map["ce-diff-previous"], yaml_map["operator-pod"],
            yaml_map["front-runner"], yaml_map["se-etype"], "/".join([yaml_map["se-namespace"],
                                                                      yaml_map["se-rtype"], yaml_map["se-name"]]))


def generate_time_travel_yaml(triggering_points, path, project, timing="after"):
    yaml_map = {}
    yaml_map["project"] = project
    yaml_map["mode"] = "time-travel"
    yaml_map["straggler"] = "kind-control-plane3"
    yaml_map["front-runner"] = "kind-control-plane"
    yaml_map["operator-pod"] = project
    yaml_map["command"] = controllers.command[project]
    yaml_map["timing"] = timing
    suffix = "-b" if timing == "before" else ""
    i = 0
    for triggering_point in triggering_points:
        if triggering_point["ttype"] != "event-delta":
            # TODO: handle the single event trigger
            continue
        i += 1
        effect = triggering_point["effect"]
        yaml_map["ce-name"] = triggering_point["name"]
        yaml_map["ce-namespace"] = triggering_point["namespace"]
        yaml_map["ce-rtype"] = triggering_point["rtype"]
        yaml_map["ce-diff-current"] = json.dumps(
            analyze_event.canonicalize_event(copy.deepcopy(triggering_point["curEvent"])))
        yaml_map["ce-diff-previous"] = json.dumps(
            analyze_event.canonicalize_event(copy.deepcopy(triggering_point["prevEvent"])))
        yaml_map["ce-etype-current"] = triggering_point["curEventType"]
        yaml_map["ce-etype-previous"] = triggering_point["prevEventType"]
        yaml_map["se-name"] = effect["name"]
        yaml_map["se-namespace"] = effect["namespace"]
        yaml_map["se-rtype"] = effect["rtype"]
        yaml_map["se-etype"] = "ADDED" if effect["etype"] == "Delete" else "DELETED"
        yaml_map["description"] = time_travel_description(yaml_map)
        yaml.dump(yaml_map, open(
            os.path.join(path, "time-travel-%s%s.yaml" % (str(i), suffix)), "w"), sort_keys=False)
    print("Generated %d time-travel config(s) in %s" % (i, path))


def dump_files(dir, event_map, causality_pairs, side_effect, status, triggering_points):
    json_dir = os.path.join(dir, "generated-json")
    if os.path.exists(json_dir):
        shutil.rmtree(json_dir)
    os.makedirs(json_dir, exist_ok=True)
    json.dump(side_effect, open(os.path.join(
        dir, "side-effect.json"), "w"), indent=4, sort_keys=True)
    json.dump(status, open(os.path.join(
        dir, "status.json"), "w"), indent=4, sort_keys=True)
    json.dump(triggering_points, open(os.path.join(
        json_dir, "triggering-points.json"), "w"), indent=4)


def analyze_trace(project, dir, double_sides=False):
    log_path = os.path.join(dir, "sonar-server.log")
    conf_dir = os.path.join(dir, "generated-config")
    if os.path.exists(conf_dir):
        shutil.rmtree(conf_dir)
    os.makedirs(conf_dir, exist_ok=True)
    causality_pairs, event_key_map = generate_event_effect_pairs(log_path)
    side_effect, status = oracle.generate_digest(log_path)
    triggering_points = generate_triggering_points(
        event_key_map, causality_pairs)
    dump_files(dir, event_key_map, causality_pairs,
               side_effect, status, triggering_points)
    generate_time_travel_yaml(triggering_points, conf_dir, project)
    if double_sides:
        generate_time_travel_yaml(
            triggering_points, conf_dir, project, "before")


if __name__ == "__main__":
    project = sys.argv[1]
    test = sys.argv[2]
    dir = os.path.join("log", project, test, "learn")
    analyze_trace(project, dir)
