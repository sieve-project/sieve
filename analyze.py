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
    largest_timestamp = len(lines)
    for i in range(len(lines)):
        line = lines[i]
        if common.SONAR_EVENT_MARK in line:
            event = common.parse_event(line)
            event.set_start_timestamp(i)
            # We initially set the event end time as the largest timestamp
            # so that if we never meet SONAR_EVENT_APPLIED_MARK for this event,
            # we will not pose any constraint on its end time in range_overlap
            event.set_end_timestamp(largest_timestamp)
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
    side_effect_list = []
    read_types_this_reconcile = set()
    read_keys_this_reconcile = set()
    prev_reconcile_start_timestamp = {}
    cur_reconcile_start_timestamp = {}
    # there could be multiple controllers running concurrently
    # we need to record all the ongoing controllers
    ongoing_reconciles = set()
    lines = open(path).readlines()
    for i in range(len(lines)):
        line = lines[i]
        if common.SONAR_SIDE_EFFECT_MARK in line:
            # If we have not met any reconcile yet, skip the side effect since it is not caused by reconcile
            # though it should not happen at all.
            if len(ongoing_reconciles) == 0:
                continue
            side_effect = common.parse_side_effect(line)
            # Do deepcopy here to ensure the later changes to the two sets
            # will not affect this side effect.
            side_effect.set_read_keys(copy.deepcopy(read_keys_this_reconcile))
            side_effect.set_read_types(
                copy.deepcopy(read_types_this_reconcile))
            side_effect.set_end_timestamp(i)
            # We want to find the earilest timestamp before which any event will not affect the side effect.
            # The earlies timestamp should be min(the timestamp of the previous reconcile start of all ongoing reconiles).
            # One special case is that at least one of the ongoing reconcile is the first reconcile of that controller.
            # In that case we will use -1 as the earliest timestamp:
            # we do not pose constraint on event end time in range_overlap.
            earliest_timestamp = i
            for controller_name in ongoing_reconciles:
                if prev_reconcile_start_timestamp[controller_name] < earliest_timestamp:
                    earliest_timestamp = prev_reconcile_start_timestamp[controller_name]
            side_effect.set_range(earliest_timestamp, i)
            side_effect_list.append(side_effect)
        elif common.SONAR_CACHE_READ_MARK in line:
            cache_read = common.parse_cache_read(line)
            if cache_read.etype == "Get":
                read_keys_this_reconcile.add(cache_read.key)
            else:
                read_types_this_reconcile.add(cache_read.rtype)
        elif common.SONAR_START_RECONCILE_MARK in line:
            reconcile = common.parse_reconcile(line)
            controller_name = reconcile.controller_name
            ongoing_reconciles.add(controller_name)
            # We use -1 as the initial value in any prev_reconcile_start_timestamp[controller_name]
            # which is super important.
            if controller_name not in cur_reconcile_start_timestamp:
                cur_reconcile_start_timestamp[controller_name] = -1
            prev_reconcile_start_timestamp[controller_name] = cur_reconcile_start_timestamp[controller_name]
            cur_reconcile_start_timestamp[controller_name] = i
        elif common.SONAR_FINISH_RECONCILE_MARK in line:
            reconcile = common.parse_reconcile(line)
            controller_name = reconcile.controller_name
            ongoing_reconciles.remove(controller_name)
            # Clear the read keys and types set since all the ongoing reconciles are done
            if len(ongoing_reconciles) == 0:
                read_keys_this_reconcile = set()
                read_types_this_reconcile = set()
    return side_effect_list


def base_pass(event_list, side_effect_list):
    print("Running base pass ...")
    event_effect_pairs = []
    for side_effect in side_effect_list:
        if side_effect.etype not in common.INTERESTING_SIDE_EFFECT_TYPE:
            continue
        for event in event_list:
            if side_effect.range_overlap(event):
                event_effect_pairs.append([event, side_effect])
    return event_effect_pairs


def write_read_overlap_filtering_pass(event_effect_pairs):
    print("Running optional pass: write-read-overlap-filtering ...")
    reduced_event_effect_pairs = []
    for pair in event_effect_pairs:
        event = pair[0]
        side_effect = pair[1]
        if side_effect.interest_overlap(event):
            reduced_event_effect_pairs.append(pair)
    return reduced_event_effect_pairs


def error_msg_filtering_pass(event_effect_pairs):
    print("Running optional pass: error-message-filtering ...")
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
    print("Analyzing %s to generate <event, side-effect> pairs ..." % path)
    event_list, event_key_map = parse_events(path)
    side_effect_list = parse_side_effects(path)
    event_effect_pairs = base_pass(event_list, side_effect_list)
    reduced_event_effect_pairs = pipelined_passes(event_effect_pairs)
    return reduced_event_effect_pairs, event_key_map


def generate_triggering_points(event_map, event_effect_pairs):
    print("Generating time-travel configs from <event, side-effect> pairs ...")
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
            if len(slim_prev_obj) == 0 and len(slim_cur_obj) == 0:
                continue
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
            yaml_map["ce-diff-current"], yaml_map["ce-diff-previous"], yaml_map["operator-pod-label"],
            yaml_map["front-runner"], yaml_map["se-etype"], "/".join([yaml_map["se-namespace"],
                                                                      yaml_map["se-rtype"], yaml_map["se-name"]]))


def generate_time_travel_yaml(triggering_points, path, project, timing="after"):
    yaml_map = {}
    yaml_map["project"] = project
    yaml_map["mode"] = "time-travel"
    yaml_map["straggler"] = controllers.straggler
    yaml_map["front-runner"] = controllers.front_runner
    yaml_map["operator-pod-label"] = controllers.operator_pod_label[project]
    yaml_map["deployment-name"] = controllers.deployment_name[project]
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
            os.path.join(path, "time-travel-config-%s%s.yaml" % (str(i), suffix)), "w"), sort_keys=False)
    print("Generated %d time-travel config(s) in %s" % (i, path))


def dump_json_file(dir, data, json_file_name):
    json.dump(data, open(os.path.join(
        dir, json_file_name), "w"), indent=4, sort_keys=True)


def analyze_trace(project, dir, double_sides=False, generate_oracle=True):
    print("double-sides feature is %s" %
          ("enabled" if double_sides else "disabled"))
    print("generate-oracle feature is %s" %
          ("enabled" if generate_oracle else "disabled"))
    log_path = os.path.join(dir, "sonar-server.log")
    conf_dir = os.path.join(dir, "generated-config")
    if os.path.exists(conf_dir):
        shutil.rmtree(conf_dir)
    os.makedirs(conf_dir, exist_ok=True)
    causality_pairs, event_key_map = generate_event_effect_pairs(log_path)
    triggering_points = generate_triggering_points(
        event_key_map, causality_pairs)
    dump_json_file(dir, triggering_points, "triggering-points.json")
    generate_time_travel_yaml(triggering_points, conf_dir, project)
    if double_sides:
        generate_time_travel_yaml(
            triggering_points, conf_dir, project, "before")
    if generate_oracle:
        side_effect, status = oracle.generate_digest(log_path)
        dump_json_file(dir, side_effect, "side-effect.json")
        dump_json_file(dir, status, "status.json")


if __name__ == "__main__":
    project = sys.argv[1]
    test = sys.argv[2]
    print("Analyzing controller trace for %s's test workload %s ..." %
          (project, test))
    dir = os.path.join("log", project, test, "learn")
    analyze_trace(project, dir, double_sides=False, generate_oracle=False)
