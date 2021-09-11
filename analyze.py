import json
import yaml
import copy
import os
import controllers
import analyze_util
import oracle
import analyze_event
import json
import optparse
import sieve_config
import analyze_sql
from common import sieve_modes


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
        if analyze_util.SIEVE_BEFORE_EVENT_MARK in line:
            event = analyze_util.parse_event(line)
            event.set_start_timestamp(i)
            # We initially set the event end time as the largest timestamp
            # so that if we never meet SIEVE_AFTER_EVENT_MARK for this event,
            # we will not pose any constraint on its end time in range_overlap
            event.set_end_timestamp(largest_timestamp)
            event_id_map[event.id] = event
        elif analyze_util.SIEVE_AFTER_EVENT_MARK in line:
            event_id_only = analyze_util.parse_event_id_only(line)
            event_id_map[event_id_only.id].set_end_timestamp(i)
    for i in range(len(lines)):
        line = lines[i]
        if analyze_util.SIEVE_BEFORE_EVENT_MARK in line:
            event = analyze_util.parse_event(line)
            if event.key not in event_key_map:
                event_key_map[event.key] = []
            event_key_map[event.key].append(event_id_map[event.id])
            event_list.append(event_id_map[event.id])
    return event_list, event_key_map, event_id_map


def parse_side_effects(path, compress_trivial_reconcile=True):
    side_effect_id_map = {}
    side_effect_list = []
    side_effect_id_to_start_ts_map = {}
    read_types_this_reconcile = set()
    read_keys_this_reconcile = set()
    prev_reconcile_start_timestamp = {}
    cur_reconcile_start_timestamp = {}
    cur_reconcile_is_trivial = {}
    # there could be multiple controllers running concurrently
    # we need to record all the ongoing controllers
    # there could be multiple workers running for a single controller
    # so we need to count each worker for each controller
    # ongoing_reconcile = { controller_name -> number of ongoing workers for this controller }
    ongoing_reconciles = {}
    lines = open(path).readlines()
    for i in range(len(lines)):
        line = lines[i]
        if analyze_util.SIEVE_BEFORE_SIDE_EFFECT_MARK in line:
            side_effect_id_only = analyze_util.parse_side_effect_id_only(line)
            side_effect_id_to_start_ts_map[side_effect_id_only.id] = i
        if analyze_util.SIEVE_AFTER_SIDE_EFFECT_MARK in line:
            for key in cur_reconcile_is_trivial:
                cur_reconcile_is_trivial[key] = False
            # If we have not met any reconcile yet, skip the side effect since it is not caused by reconcile
            # though it should not happen at all.
            if len(ongoing_reconciles) == 0:
                continue
            side_effect = analyze_util.parse_side_effect(line)
            # Do deepcopy here to ensure the later changes to the two sets
            # will not affect this side effect.
            # cache read during that possible interval
            side_effect.set_read_keys(copy.deepcopy(read_keys_this_reconcile))
            side_effect.set_read_types(
                copy.deepcopy(read_types_this_reconcile))
            side_effect.set_start_timestamp(
                side_effect_id_to_start_ts_map[side_effect.id])
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
            side_effect_id_map[side_effect.id] = side_effect
        elif analyze_util.SIEVE_AFTER_READ_MARK in line:
            cache_read = analyze_util.parse_cache_read(line)
            if cache_read.etype == "Get":
                read_keys_this_reconcile.add(cache_read.key)
            else:
                read_types_this_reconcile.add(cache_read.rtype)
        elif analyze_util.SIEVE_BEFORE_RECONCILE_MARK in line:
            reconcile = analyze_util.parse_reconcile(line)
            controller_name = reconcile.controller_name
            if controller_name not in ongoing_reconciles:
                ongoing_reconciles[controller_name] = 1
            else:
                ongoing_reconciles[controller_name] += 1
            # let's assume there should be only one worker for each controller here
            assert ongoing_reconciles[controller_name] == 1
            # We use -1 as the initial value in any prev_reconcile_start_timestamp[controller_name]
            # which is super important.
            if controller_name not in cur_reconcile_start_timestamp:
                cur_reconcile_start_timestamp[controller_name] = -1
                cur_reconcile_is_trivial[controller_name] = False
            if (not compress_trivial_reconcile) or (compress_trivial_reconcile and not cur_reconcile_is_trivial[controller_name]):
                # When compress_trivial_reconcile is disabled, we directly set prev_reconcile_start_timestamp
                # When compress_trivial_reconcile is enabled, we do not set prev_reconcile_start_timestamp
                # if no side effects happen during the last reconcile
                prev_reconcile_start_timestamp[controller_name] = cur_reconcile_start_timestamp[controller_name]
            cur_reconcile_start_timestamp[controller_name] = i
            # Reset cur_reconcile_is_trivial[controller_name] to True as a new round of reconcile just starts
            cur_reconcile_is_trivial[controller_name] = True
        elif analyze_util.SIEVE_AFTER_RECONCILE_MARK in line:
            reconcile = analyze_util.parse_reconcile(line)
            controller_name = reconcile.controller_name
            ongoing_reconciles[controller_name] -= 1
            if ongoing_reconciles[controller_name] == 0:
                del ongoing_reconciles[controller_name]
            # Clear the read keys and types set since all the ongoing reconciles are done
            if len(ongoing_reconciles) == 0:
                read_keys_this_reconcile = set()
                read_types_this_reconcile = set()
    for i in range(len(lines)):
        line = lines[i]
        if analyze_util.SIEVE_BEFORE_SIDE_EFFECT_MARK in line:
            side_effect_id = analyze_util.parse_side_effect_id_only(line)
            if side_effect_id.id in side_effect_id_map:
                side_effect_list.append(side_effect_id_map[side_effect_id.id])
    return side_effect_list, side_effect_id_map


def base_pass(analysis_mode, event_list, side_effect_list):
    print("Running base pass ...")
    event_effect_pairs = []
    for side_effect in side_effect_list:
        for event in event_list:
            # events can lead to that side_effect
            if side_effect.range_overlap(event):
                event_effect_pairs.append([event, side_effect])
    return event_effect_pairs


def delete_only_filtering_pass(analysis_mode, event_effect_pairs):
    print("Running optional pass: delete-only-filtering ...")
    reduced_event_effect_pairs = []
    for pair in event_effect_pairs:
        side_effect = pair[1]
        if side_effect.etype == "Delete":
            reduced_event_effect_pairs.append(pair)
    print("<e, s> pairs: %d -> %d" %
          (len(event_effect_pairs), len(reduced_event_effect_pairs)))
    return reduced_event_effect_pairs


def write_read_overlap_filtering_pass(analysis_mode, event_effect_pairs):
    print("Running optional pass: write-read-overlap-filtering ...")
    reduced_event_effect_pairs = []
    for pair in event_effect_pairs:
        event = pair[0]
        side_effect = pair[1]
        if side_effect.interest_overlap(event):
            reduced_event_effect_pairs.append(pair)
    print("<e, s> pairs: %d -> %d" %
          (len(event_effect_pairs), len(reduced_event_effect_pairs)))
    return reduced_event_effect_pairs


def error_msg_filtering_pass(analysis_mode, event_effect_pairs):
    print("Running optional pass: error-message-filtering ...")
    reduced_event_effect_pairs = []
    for pair in event_effect_pairs:
        side_effect = pair[1]
        if side_effect.error in analyze_util.ALLOWED_ERROR_TYPE:
            reduced_event_effect_pairs.append(pair)
    print("<e, s> pairs: %d -> %d" %
          (len(event_effect_pairs), len(reduced_event_effect_pairs)))
    return reduced_event_effect_pairs


def pipelined_passes(analysis_mode, event_effect_pairs):
    reduced_event_effect_pairs = event_effect_pairs
    if analyze_util.DELETE_ONLY_FILTER_FLAG and analysis_mode == sieve_modes.TIME_TRAVEL:
        reduced_event_effect_pairs = delete_only_filtering_pass(
            analysis_mode, reduced_event_effect_pairs)
    if analyze_util.ERROR_MSG_FILTER_FLAG:
        reduced_event_effect_pairs = error_msg_filtering_pass(
            analysis_mode, reduced_event_effect_pairs)
    if analyze_util.WRITE_READ_FILTER_FLAG:
        reduced_event_effect_pairs = write_read_overlap_filtering_pass(
            analysis_mode, reduced_event_effect_pairs)
    return reduced_event_effect_pairs


def intra_pair_analysis(analysis_mode, use_sql, event_list, event_id_map, side_effect_list, side_effect_id_map):
    reduced_event_effect_pairs = []
    if use_sql:
        conn = analyze_sql.create_sqlite_db()
        analyze_sql.record_event_list_in_sqlite(event_list, conn)
        analyze_sql.record_side_effect_list_in_sqlite(side_effect_list, conn)
        cur = conn.cursor()
        query = analyze_sql.passes_as_sql_query(analysis_mode)
        print("Running SQL query as below ...")
        print(query)
        cur.execute(query)
        rows = cur.fetchall()
        for row in rows:
            event_id = row[0]
            side_effect_id = row[1]
            reduced_event_effect_pairs.append(
                [event_id_map[event_id], side_effect_id_map[side_effect_id]])
    else:
        event_effect_pairs = base_pass(
            analysis_mode, event_list, side_effect_list)
        reduced_event_effect_pairs = pipelined_passes(
            analysis_mode, event_effect_pairs)
    return reduced_event_effect_pairs


def inter_pair_analysis(analysis_mode, event_effect_pairs, event_key_map):
    if analysis_mode == sieve_modes.TIME_TRAVEL:
        reduced_event_effect_pairs = delete_then_recreate_filtering_pass(
            event_effect_pairs, event_key_map)
        return reduced_event_effect_pairs
    else:
        return event_effect_pairs


def sanity_check_sieve_log(path):
    lines = open(path).readlines()
    reconcile_status = {}
    side_effect_status = {}
    event_status = {}
    for i in range(len(lines)):
        line = lines[i]
        if analyze_util.SIEVE_BEFORE_SIDE_EFFECT_MARK in line:
            side_effect_id = analyze_util.parse_side_effect_id_only(line).id
            assert side_effect_id not in side_effect_status
            side_effect_status[side_effect_id] = 1
        elif analyze_util.SIEVE_AFTER_SIDE_EFFECT_MARK in line:
            side_effect_id = analyze_util.parse_side_effect_id_only(line).id
            assert side_effect_id in side_effect_status
            side_effect_status[side_effect_id] += 1
        elif analyze_util.SIEVE_BEFORE_EVENT_MARK in line:
            event_id = analyze_util.parse_event_id_only(line).id
            assert event_id not in event_status
            event_status[event_id] = 1
        elif analyze_util.SIEVE_AFTER_EVENT_MARK in line:
            event_id = analyze_util.parse_event_id_only(line).id
            assert event_id in event_status
            event_status[event_id] += 1
        elif analyze_util.SIEVE_BEFORE_RECONCILE_MARK in line:
            reconcile_id = analyze_util.parse_reconcile(line).controller_name
            if reconcile_id not in reconcile_status:
                reconcile_status[reconcile_id] = 0
            reconcile_status[reconcile_id] += 1
            assert reconcile_status[reconcile_id] == 1
        elif analyze_util.SIEVE_AFTER_RECONCILE_MARK in line:
            assert reconcile_id in reconcile_status
            reconcile_status[reconcile_id] -= 1
            assert reconcile_status[reconcile_id] == 0
    for key in side_effect_status:
        assert side_effect_status[key] == 1 or side_effect_status[key] == 2
    for key in event_status:
        assert event_status[key] == 1 or event_status[key] == 2
    for key in reconcile_status:
        assert reconcile_status[reconcile_id] == 0 or reconcile_status[reconcile_id] == 1


def extract_events_and_effects(path, compress_trivial_reconcile):
    event_list, event_key_map, event_id_map = parse_events(path)
    side_effect_list, side_effect_id_map = parse_side_effects(
        path, compress_trivial_reconcile)
    return event_list, event_key_map, event_id_map, side_effect_list, side_effect_id_map


def generate_event_effect_pairs(analysis_mode, path, use_sql, event_list, event_key_map, event_id_map, side_effect_list, side_effect_id_map):
    print("Analyzing %s to generate <event, side-effect> pairs ..." % path)
    after_intra_pairs = intra_pair_analysis(
        analysis_mode, use_sql, event_list, event_id_map, side_effect_list, side_effect_id_map)
    after_inter_pairs = inter_pair_analysis(
        analysis_mode, after_intra_pairs, event_key_map)
    return after_inter_pairs


def generate_effect_event_pairs(event_list, side_effect_list, event_key_map):
    effect_event_pairs = []
    for side_effect in side_effect_list:
        assert isinstance(side_effect, analyze_util.SideEffect)
        if side_effect.key in event_key_map:
            for event in event_list:
                assert isinstance(event, analyze_util.Event)
                if event.obj_str == side_effect.obj_str and side_effect.start_timestamp < event.start_timestamp and analyze_util.consistent_type(event.etype, side_effect.etype):
                    effect_event_pairs.append([side_effect, event])
                    break
    return effect_event_pairs


def generate_triggering_points(event_map, event_effect_pairs):
    print("Generating triggering points from <event, side-effect> pairs ...")
    triggering_points = []
    for pair in event_effect_pairs:
        event = pair[0]
        side_effect = pair[1]
        prev_event, cur_event = analyze_event.find_previous_event(
            event, event_map)
        triggering_point = {"name": cur_event.name,
                            "namespace": cur_event.namespace,
                            "rtype": cur_event.rtype,
                            "effect": side_effect.to_dict(),
                            "curEventId": cur_event.id}
        if prev_event is None:
            continue
            # TODO: how to deal with the first event of each resource?
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


def obs_gap_description(yaml_map):
    return "Pause any reconcile on %s after it sees a %s event E. "\
        "E should match the pattern %s and the events before E should match %s. "\
        "And resume reconcile on the controller %s after it sees an event cancel event E." % (
            yaml_map["operator-pod-label"], "/".join([yaml_map["ce-namespace"],
                                                      yaml_map["ce-rtype"], yaml_map["ce-name"]]),
            yaml_map["ce-diff-current"], yaml_map["ce-diff-previous"], yaml_map["operator-pod-label"],
        )


def generate_time_travel_yaml(triggering_points, path, project, timing="after"):
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
    for triggering_point in triggering_points:
        assert triggering_point["ttype"] == "event-delta"
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


def generate_obs_gap_yaml(triggering_points, path, project):
    yaml_map = {}
    yaml_map["project"] = project
    yaml_map["stage"] = "test"
    yaml_map["mode"] = sieve_modes.OBS_GAP
    yaml_map["operator-pod-label"] = controllers.operator_pod_label[project]
    i = 0
    events_set = set()
    for triggering_point in triggering_points:
        if triggering_point["curEventId"] not in events_set:
            events_set.add(triggering_point["curEventId"])
        else:
            continue
        assert triggering_point["ttype"] == "event-delta"
        i += 1
        yaml_map["ce-name"] = triggering_point["name"]
        yaml_map["ce-namespace"] = triggering_point["namespace"]
        yaml_map["ce-rtype"] = triggering_point["rtype"]
        yaml_map["ce-diff-current"] = json.dumps(
            analyze_event.canonicalize_event(copy.deepcopy(triggering_point["curEvent"])))
        yaml_map["ce-diff-previous"] = json.dumps(
            analyze_event.canonicalize_event(copy.deepcopy(triggering_point["prevEvent"])))
        yaml_map["ce-etype-current"] = triggering_point["curEventType"]
        yaml_map["ce-etype-previous"] = triggering_point["prevEventType"]
        yaml_map["description"] = obs_gap_description(yaml_map)
        yaml.dump(yaml_map, open(
            os.path.join(path, "obs-gap-config-%s.yaml" % (str(i))), "w"), sort_keys=False)
    print("Generated %d obs-gap config(s) in %s" % (i, path))


def generate_atomic_yaml(triggering_points, path, project):
    yaml_map = {}
    yaml_map["project"] = project
    yaml_map["stage"] = "test"
    yaml_map["mode"] = sieve_modes.ATOM_VIO
    yaml_map["front-runner"] = sieve_config.config["time_travel_front_runner"]
    yaml_map["operator-pod-label"] = controllers.operator_pod_label[project]
    yaml_map["deployment-name"] = controllers.deployment_name[project]
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
        yaml_map["se-etype"] = effect["etype"]
        # TODO: should find a way to determine crash location
        yaml_map["crash-location"] = "before"
        yaml_map["description"] = ""
        yaml.dump(yaml_map, open(
            os.path.join(path, "atomic-config-%s.yaml" % (str(i))), "w"), sort_keys=False)
    print("Generated %d atomic config(s) in %s" % (i, path))


def dump_json_file(dir, data, json_file_name):
    json.dump(data, open(os.path.join(
        dir, json_file_name), "w"), indent=4, sort_keys=True)


def delete_then_recreate_filtering_pass(causality_pairs, event_key_map):
    print("Running optional pass: delete-then-recreate-filtering ...")
    # this should only be applied to time travel mode
    filtered_causality_pairs = []
    for pair in causality_pairs:
        side_effect = pair[1]
        # time travel only cares about delete for now
        assert side_effect.etype == "Delete"
        keep_this_pair = False
        if side_effect.key in event_key_map:
            for event in event_key_map[side_effect.key]:
                # We will find add sth
                if event.start_timestamp <= side_effect.end_timestamp:
                    continue
                if event.etype == "Added":
                    keep_this_pair = True
        else:
            # if the side effect key never appears in the event_key_map
            # it means the operator does not watch on the resource
            # so we should be cautious and keep this pair
            keep_this_pair = True
        if keep_this_pair:
            filtered_causality_pairs.append(pair)
    print("<e, s> pairs: %d -> %d" %
          (len(causality_pairs), len(filtered_causality_pairs)))
    return filtered_causality_pairs


def generate_test_config(analysis_mode, project, log_dir, two_sided, use_sql, compress_trivial_reconcile):
    log_path = os.path.join(log_dir, "sieve-server.log")
    print("Sanity checking the sieve log %s ..." % log_path)
    sanity_check_sieve_log(log_path)
    event_list, event_key_map, event_id_map, side_effect_list, side_effect_id_map = extract_events_and_effects(
        log_path, compress_trivial_reconcile)
    causality_pairs = generate_event_effect_pairs(
        analysis_mode, log_path, use_sql, event_list, event_key_map, event_id_map, side_effect_list, side_effect_id_map)
    triggering_points = generate_triggering_points(
        event_key_map, causality_pairs)
    dump_json_file(log_dir, triggering_points,
                   "triggering-points.json")
    generated_config_dir = os.path.join(
        log_dir, analysis_mode)
    os.makedirs(generated_config_dir, exist_ok=True)
    if analysis_mode == sieve_modes.TIME_TRAVEL:
        generate_time_travel_yaml(
            triggering_points, generated_config_dir, project)
        if two_sided:
            generate_time_travel_yaml(
                triggering_points, generated_config_dir, project, "before")
    elif analysis_mode == sieve_modes.OBS_GAP:
        generate_obs_gap_yaml(
            triggering_points, generated_config_dir, project)
    elif analysis_mode == sieve_modes.ATOM_VIO:
        generate_atomic_yaml(
            triggering_points, generated_config_dir, project)


def generate_test_oracle(log_dir):
    log_path = os.path.join(log_dir, "sieve-server.log")
    side_effect, status, resources = oracle.generate_digest(log_path)
    dump_json_file(log_dir, side_effect, "side-effect.json")
    dump_json_file(log_dir, status, "status.json")
    dump_json_file(log_dir, resources, "resources.json")


def analyze_trace(project, log_dir, generate_oracle=True, generate_config=True, two_sided=False, use_sql=False, compress_trivial_reconcile=True):
    print("generate-oracle feature is %s" %
          ("enabled" if generate_oracle else "disabled"))
    print("generate-config feature is %s" %
          ("enabled" if generate_config else "disabled"))
    if not generate_config:
        two_sided = False
        use_sql = False
    print("two-sided feature is %s" %
          ("enabled" if two_sided else "disabled"))
    print("use-sql feature is %s" %
          ("enabled" if use_sql else "disabled"))

    if generate_config:
        for analysis_mode in [sieve_modes.TIME_TRAVEL, sieve_modes.OBS_GAP, sieve_modes.ATOM_VIO]:
            generate_test_config(analysis_mode, project, log_dir,
                                 two_sided, use_sql, compress_trivial_reconcile)

    if generate_oracle:
        generate_test_oracle(log_dir)


if __name__ == "__main__":
    usage = "usage: python3 analyze.py [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-p", "--project", dest="project",
                      help="specify PROJECT", metavar="PROJECT", default="cassandra-operator")
    parser.add_option("-t", "--test", dest="test",
                      help="specify TEST to run", metavar="TEST", default="recreate")
    (options, args) = parser.parse_args()
    project = options.project
    test = options.test
    print("Analyzing controller trace for %s's test workload %s ..." %
          (project, test))
    # hardcoded to time travel config only for now
    dir = os.path.join("log", project, test, "learn", "learn")
    analyze_trace(project, dir, generate_oracle=False,
                  generate_config=True, two_sided=False, use_sql=False, compress_trivial_reconcile=True)
