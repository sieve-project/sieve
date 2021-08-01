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
import sqlite3
import json
import optparse


def create_sqlite_db():
    database = "/tmp/test.db"
    conn = sqlite3.connect(database)
    conn.execute("drop table if exists events")
    conn.execute("drop table if exists side_effects")

    # TODO: SQlite3 does not type check by default, but
    # tighten the column types later
    conn.execute('''
        create table events
        (
           id integer not null primary key,
           sonar_event_id integer not null,
           event_type text not null,
           resource_type text not null,
           json_object text not null,
           namespace text not null,
           name text not null,
           event_arrival_time integer not null,
           event_cache_update_time integer not null,
           fully_qualified_name text not null
        )
    ''')
    conn.execute('''
        create table side_effects
        (
           id integer not null primary key,
           sonar_side_effect_id integer not null,
           event_type text not null,
           resource_type text not null,
           namespace text not null,
           name text not null,
           error text not null,
           read_types text not null,
           read_fully_qualified_names text not null,
           range_start_timestamp integer not null,
           range_end_timestamp integer not null,
           end_timestamp integer not null,
           owner_controllers text not null
        )
    ''')
    return conn


def record_event_list_in_sqlite(event_list, conn):
    for e in event_list:
        json_form = json.dumps(e.obj)
        # Skip the first column: Sqlite will use an auto-incrementing ID
        conn.execute("insert into events values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (None, e.id, e.etype, e.rtype, json_form, e.namespace, e.name, e.start_timestamp, e.end_timestamp, e.key))
    conn.commit()


def record_side_effect_list_in_sqlite(side_effect_list, conn):
    for e in side_effect_list:
        json_read_types = json.dumps(list(e.read_types))
        json_read_keys = json.dumps(list(e.read_keys))
        json_owner_controllers = json.dumps(list(e.owner_controllers))
        # Skip the first column: Sqlite will use an auto-incrementing ID
        conn.execute("insert into side_effects values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (None, e.id, e.etype, e.rtype, e.namespace, e.name, e.error, json_read_types, json_read_keys, e.range_start_timestamp, e.range_end_timestamp, e.end_timestamp, json_owner_controllers))
    conn.commit()


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
    return event_list, event_key_map, event_id_map


def parse_side_effects(path, compress_trivial_reconcile=True):
    side_effect_id_map = {}
    side_effect_list = []
    read_types_this_reconcile = set()
    read_keys_this_reconcile = set()
    prev_reconcile_start_timestamp = {}
    cur_reconcile_start_timestamp = {}
    cur_reconcile_is_trivial = {}
    # there could be multiple controllers running concurrently
    # we need to record all the ongoing controllers
    ongoing_reconciles = set()
    lines = open(path).readlines()
    for i in range(len(lines)):
        line = lines[i]
        if common.SONAR_SIDE_EFFECT_MARK in line:
            for key in cur_reconcile_is_trivial:
                cur_reconcile_is_trivial[key] = False
            # If we have not met any reconcile yet, skip the side effect since it is not caused by reconcile
            # though it should not happen at all.
            if len(ongoing_reconciles) == 0:
                continue
            side_effect = common.parse_side_effect(line)
            # Do deepcopy here to ensure the later changes to the two sets
            # will not affect this side effect.
            # cache read during that possible interval
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
            side_effect_id_map[side_effect.id] = side_effect
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
                cur_reconcile_is_trivial[controller_name] = False
            if (not compress_trivial_reconcile) or (compress_trivial_reconcile and not cur_reconcile_is_trivial[controller_name]):
                # When compress_trivial_reconcile is disabled, we directly set prev_reconcile_start_timestamp
                # When compress_trivial_reconcile is enabled, we do not set prev_reconcile_start_timestamp
                # if no side effects happen during the last reconcile
                prev_reconcile_start_timestamp[controller_name] = cur_reconcile_start_timestamp[controller_name]
            cur_reconcile_start_timestamp[controller_name] = i
            # Reset cur_reconcile_is_trivial[controller_name] to True as a new round of reconcile just starts
            cur_reconcile_is_trivial[controller_name] = True
        elif common.SONAR_FINISH_RECONCILE_MARK in line:
            reconcile = common.parse_reconcile(line)
            controller_name = reconcile.controller_name
            ongoing_reconciles.remove(controller_name)
            # Clear the read keys and types set since all the ongoing reconciles are done
            if len(ongoing_reconciles) == 0:
                read_keys_this_reconcile = set()
                read_types_this_reconcile = set()
    return side_effect_list, side_effect_id_map


def base_pass(mode, event_list, side_effect_list):
    print("Running base pass ...")
    event_effect_pairs = []
    for side_effect in side_effect_list:
        for event in event_list:
            # events can lead to that side_effect
            if side_effect.range_overlap(event):
                event_effect_pairs.append([event, side_effect])
    return event_effect_pairs


def delete_only_filtering_pass(mode, event_effect_pairs):
    print("Running optional pass: delete-only-filtering ...")
    reduced_event_effect_pairs = []
    for pair in event_effect_pairs:
        side_effect = pair[1]
        if side_effect.etype == "Delete":
            reduced_event_effect_pairs.append(pair)
    return reduced_event_effect_pairs


def write_read_overlap_filtering_pass(mode, event_effect_pairs):
    print("Running optional pass: write-read-overlap-filtering ...")
    reduced_event_effect_pairs = []
    for pair in event_effect_pairs:
        event = pair[0]
        side_effect = pair[1]
        if side_effect.interest_overlap(event):
            reduced_event_effect_pairs.append(pair)
    return reduced_event_effect_pairs


def error_msg_filtering_pass(mode, event_effect_pairs):
    print("Running optional pass: error-message-filtering ...")
    reduced_event_effect_pairs = []
    for pair in event_effect_pairs:
        side_effect = pair[1]
        if side_effect.error not in common.FILTERED_ERROR_TYPE:
            reduced_event_effect_pairs.append(pair)
    return reduced_event_effect_pairs


def pipelined_passes(mode, event_effect_pairs):
    reduced_event_effect_pairs = event_effect_pairs
    if common.DELETE_ONLY_FILTER_FLAG and mode == "time-travel":
        reduced_event_effect_pairs = delete_only_filtering_pass(
            mode, reduced_event_effect_pairs)
    if common.ERROR_MSG_FILTER_FLAG:
        reduced_event_effect_pairs = error_msg_filtering_pass(
            mode, reduced_event_effect_pairs)
    if common.WRITE_READ_FILTER_FLAG:
        reduced_event_effect_pairs = write_read_overlap_filtering_pass(
            mode, reduced_event_effect_pairs)
    return reduced_event_effect_pairs


def passes_as_sql_query():
    query = common.SQL_BASE_PASS_QUERY
    first_optional_pass = True
    if common.DELETE_ONLY_FILTER_FLAG:
        query += " where " if first_optional_pass else " and "
        query += common.SQL_DELETE_ONLY_FILTER
        first_optional_pass = False
    if common.ERROR_MSG_FILTER_FLAG:
        query += " where " if first_optional_pass else " and "
        query += common.SQL_ERROR_MSG_FILTER
        first_optional_pass = False
    if common.WRITE_READ_FILTER_FLAG:
        query += " where " if first_optional_pass else " and "
        query += common.SQL_WRITE_READ_FILTER
        first_optional_pass = False
    return query


def generate_event_effect_pairs(mode, path, use_sql, compress_trivial_reconcile):
    print("Analyzing %s to generate <event, side-effect> pairs ..." % path)
    event_list, event_key_map, event_id_map = parse_events(path)
    side_effect_list, side_effect_id_map = parse_side_effects(
        path, compress_trivial_reconcile)
    reduced_event_effect_pairs = []
    if use_sql:
        conn = create_sqlite_db()
        record_event_list_in_sqlite(event_list, conn)
        record_side_effect_list_in_sqlite(side_effect_list, conn)
        cur = conn.cursor()
        query = passes_as_sql_query()
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
        event_effect_pairs = base_pass(mode, event_list, side_effect_list)
        reduced_event_effect_pairs = pipelined_passes(mode, event_effect_pairs)
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

def obs_gap_description(yaml_map):
    return "Pause any reconcile on %s after it sees a %s event E. "\
        "E should match the pattern %s and the events before E should match %s. "\
        "And resume reconcile on the controller %s after it sees an event cancel event E." % (
            yaml_map["operator-pod-label"], "/".join([yaml_map["ce-namespace"],
                                             yaml_map["ce-rtype"], yaml_map["ce-name"]]),
            yaml_map["ce-diff-current"], yaml_map["ce-diff-previous"], yaml_map["operator-pod-label"],
            )

def generate_time_travel_yaml(triggering_points, path, project, node_ignore, timing="after"):
    yaml_map = {}
    yaml_map["project"] = project
    yaml_map["stage"] = "test"
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
            analyze_event.canonicalize_event(copy.deepcopy(triggering_point["curEvent"]), node_ignore))
        yaml_map["ce-diff-previous"] = json.dumps(
            analyze_event.canonicalize_event(copy.deepcopy(triggering_point["prevEvent"]), node_ignore))
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


def generate_obs_gap_yaml(triggering_points, path, project, node_ignore):
    yaml_map = {}
    yaml_map["project"] = project
    yaml_map["stage"] = "test"
    yaml_map["mode"] = "obs-gap"
    yaml_map["straggler"] = controllers.straggler
    yaml_map["front-runner"] = controllers.front_runner
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
            analyze_event.canonicalize_event(copy.deepcopy(triggering_point["curEvent"]), node_ignore))
        yaml_map["ce-diff-previous"] = json.dumps(
            analyze_event.canonicalize_event(copy.deepcopy(triggering_point["prevEvent"]), node_ignore))
        yaml_map["ce-etype-current"] = triggering_point["curEventType"]
        yaml_map["ce-etype-previous"] = triggering_point["prevEventType"]
        yaml_map["se-name"] = effect["name"]
        yaml_map["se-namespace"] = effect["namespace"]
        yaml_map["se-rtype"] = effect["rtype"]
        yaml_map["se-etype"] = effect["etype"]
        yaml_map["description"] = obs_gap_description(yaml_map)
        yaml.dump(yaml_map, open(
            os.path.join(path, "obs-gap-config-%s.yaml" % (str(i))), "w"), sort_keys=False)
    print("Generated %d obs-gap config(s) in %s" % (i, path))

def generate_atomic_yaml(triggering_points, path, project, node_ignore):
    yaml_map = {}
    yaml_map["project"] = project
    yaml_map["stage"] = "test"
    yaml_map["mode"] = "atomic"
    yaml_map["straggler"] = controllers.straggler
    yaml_map["front-runner"] = controllers.front_runner
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
            analyze_event.canonicalize_event(copy.deepcopy(triggering_point["curEvent"]), node_ignore))
        yaml_map["ce-diff-previous"] = json.dumps(
            analyze_event.canonicalize_event(copy.deepcopy(triggering_point["prevEvent"]), node_ignore))
        yaml_map["ce-etype-current"] = triggering_point["curEventType"]
        yaml_map["ce-etype-previous"] = triggering_point["prevEventType"]
        yaml_map["se-name"] = effect["name"]
        yaml_map["se-namespace"] = effect["namespace"]
        yaml_map["se-rtype"] = effect["rtype"]
        yaml_map["se-etype"] = effect["etype"]
        yaml_map["description"] = ""
        yaml.dump(yaml_map, open(
            os.path.join(path, "atomic-config-%s.yaml" % (str(i))), "w"), sort_keys=False)
    print("Generated %d atomic config(s) in %s" % (i, path))

def dump_json_file(dir, data, json_file_name):
    json.dump(data, open(os.path.join(
        dir, json_file_name), "w"), indent=4, sort_keys=True)

def side_effect_filter(causality_pairs, event_key_map):
    filtered_causality_pairs = []
    for pair in causality_pairs:
        start_event = pair[0]
        side_effect = pair[1] # e.g. delete sth
        # Ignore if side effect is not delete
        if not side_effect.etype == "Delete":
            filtered_causality_pairs.append(pair)
            continue
        flag = False
        if side_effect.key in event_key_map:
            for event in event_key_map[side_effect.key]:
                # We will find add sth
                if event.start_timestamp <= side_effect.end_timestamp:
                    continue
                if event.etype == "Added":
                    flag = True
        if flag:
            filtered_causality_pairs.append(pair)
    print("side effect filter reduce causality_pairs from %d to %d"%(len(causality_pairs), len(filtered_causality_pairs)))
    return filtered_causality_pairs

def analyze_trace(project, log_dir, conf_dir, mode, generate_oracle=True, generate_config=True, two_sided=False, node_ignore=(True, []), se_filter=False, use_sql=True, compress_trivial_reconcile=True):
    use_sql = False # Temp disable for CI
    print("generate-oracle feature is %s" %
          ("enabled" if generate_oracle else "disabled"))
    print("generate-config feature is %s" %
          ("enabled" if generate_config else "disabled"))
    if not generate_config:
        two_sided = False
        use_sql = False
    # Disable sql feature for obs gap / atomic mode for now
    if mode == "obs-gap" or mode == "atomic":
        use_sql = False
    print("two-sided feature is %s" %
          ("enabled" if two_sided else "disabled"))
    print("use-sql feature is %s" %
          ("enabled" if use_sql else "disabled"))
    conf_path = os.path.join(conf_dir, "sonar-server.log")
    if generate_config:
        if os.path.exists(log_dir):
            shutil.rmtree(log_dir)
        os.makedirs(log_dir, exist_ok=True)
        causality_pairs, event_key_map = generate_event_effect_pairs(
            mode, conf_path, use_sql, compress_trivial_reconcile)
        if se_filter:
            causality_pairs = side_effect_filter(causality_pairs, event_key_map)
        triggering_points = generate_triggering_points(
            event_key_map, causality_pairs)
        dump_json_file(conf_dir, triggering_points, "triggering-points.json")
        if mode == "time-travel":
            generate_time_travel_yaml(triggering_points, log_dir, project, node_ignore)
            if two_sided:
                generate_time_travel_yaml(
                    triggering_points, log_dir, project, node_ignore, "before")
        elif mode == "obs-gap":
            generate_obs_gap_yaml(triggering_points, log_dir, project, node_ignore)
        elif mode == "atomic":
            generate_atomic_yaml(triggering_points, log_dir, project, node_ignore)

    if generate_oracle:
        side_effect, status, resources = oracle.generate_digest(conf_path)
        dump_json_file(conf_dir, side_effect, "side-effect.json")
        dump_json_file(conf_dir, status, "status.json")
        dump_json_file(conf_dir, resources, "resources.json")


if __name__ == "__main__":
    usage = "usage: python3 analyze.py [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-p", "--project", dest="project",
                      help="specify PROJECT to test: cassandra-operator or zookeeper-operator", metavar="PROJECT", default="cassandra-operator")
    parser.add_option("-t", "--test", dest="test",
                      help="specify TEST to run", metavar="TEST", default="recreate")
    (options, args) = parser.parse_args()
    project = options.project
    test = options.test
    print("Analyzing controller trace for %s's test workload %s ..." %
          (project, test))
    # hardcoded to time travel config only for now
    dir = os.path.join("log", project, "learn", test, "time-travel")
    analyze_trace(project, dir, "time-travel", generate_oracle=False,
                  generate_config=True, two_sided=False, use_sql=False, compress_trivial_reconcile=True)
