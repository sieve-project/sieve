from typing import List
import copy
import os
from analyze_util import *
import oracle
import shutil
import optparse
import analyze_gen
from common import sieve_modes


def sanity_check_sieve_log(path):
    lines = open(path).readlines()
    reconcile_status = {}
    side_effect_status = {}
    event_status = {}
    for i in range(len(lines)):
        line = lines[i]
        if SIEVE_BEFORE_SIDE_EFFECT_MARK in line:
            side_effect_id = parse_side_effect_id_only(line).id
            assert side_effect_id not in side_effect_status
            side_effect_status[side_effect_id] = 1
        elif SIEVE_AFTER_SIDE_EFFECT_MARK in line:
            side_effect_id = parse_side_effect_id_only(line).id
            assert side_effect_id in side_effect_status
            side_effect_status[side_effect_id] += 1
        elif SIEVE_BEFORE_EVENT_MARK in line:
            event_id = parse_event_id_only(line).id
            assert event_id not in event_status
            event_status[event_id] = 1
        elif SIEVE_AFTER_EVENT_MARK in line:
            event_id = parse_event_id_only(line).id
            assert event_id in event_status
            event_status[event_id] += 1
        elif SIEVE_BEFORE_RECONCILE_MARK in line:
            reconcile_id = parse_reconcile(line).controller_name
            if reconcile_id not in reconcile_status:
                reconcile_status[reconcile_id] = 0
            reconcile_status[reconcile_id] += 1
            assert reconcile_status[reconcile_id] == 1
        elif SIEVE_AFTER_RECONCILE_MARK in line:
            assert reconcile_id in reconcile_status
            reconcile_status[reconcile_id] -= 1
            assert reconcile_status[reconcile_id] == 0
    for key in side_effect_status:
        assert side_effect_status[key] == 1 or side_effect_status[key] == 2
    for key in event_status:
        assert event_status[key] == 1 or event_status[key] == 2
    for key in reconcile_status:
        assert (
            reconcile_status[reconcile_id] == 0 or reconcile_status[reconcile_id] == 1
        )


def parse_events(path):
    # { event id -> event }
    event_id_map = {}
    # { event key -> [events belonging to the key] }
    # we need this map to later find the previous event for each crucial event
    event_list = []
    lines = open(path).readlines()
    largest_timestamp = len(lines)
    for i in range(len(lines)):
        line = lines[i]
        if SIEVE_BEFORE_EVENT_MARK in line:
            event = parse_event(line)
            event.start_timestamp = i
            # We initially set the event end time as the largest timestamp
            # so that if we never meet SIEVE_AFTER_EVENT_MARK for this event,
            # we will not pose any constraint on its end time in range_overlap
            event.end_timestamp = largest_timestamp
            event_id_map[event.id] = event
        elif SIEVE_AFTER_EVENT_MARK in line:
            event_id_only = parse_event_id_only(line)
            event_id_map[event_id_only.id].end_timestamp = i
    for i in range(len(lines)):
        line = lines[i]
        if SIEVE_BEFORE_EVENT_MARK in line:
            event = parse_event(line)
            event_list.append(event_id_map[event.id])
    return event_list


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
        if SIEVE_BEFORE_SIDE_EFFECT_MARK in line:
            side_effect_id_only = parse_side_effect_id_only(line)
            side_effect_id_to_start_ts_map[side_effect_id_only.id] = i
        if SIEVE_AFTER_SIDE_EFFECT_MARK in line:
            for key in cur_reconcile_is_trivial:
                cur_reconcile_is_trivial[key] = False
            # If we have not met any reconcile yet, skip the side effect since it is not caused by reconcile
            # though it should not happen at all.
            if len(ongoing_reconciles) == 0:
                continue
            side_effect = parse_side_effect(line)
            # Do deepcopy here to ensure the later changes to the two sets
            # will not affect this side effect.
            # cache read during that possible interval
            side_effect.read_keys = copy.deepcopy(read_keys_this_reconcile)
            side_effect.read_types = copy.deepcopy(read_types_this_reconcile)
            side_effect.start_timestamp = side_effect_id_to_start_ts_map[side_effect.id]
            side_effect.end_timestamp = i
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
        elif SIEVE_AFTER_READ_MARK in line:
            cache_read = parse_cache_read(line)
            if cache_read.etype == "Get":
                read_keys_this_reconcile.add(cache_read.key)
            else:
                read_types_this_reconcile.add(cache_read.rtype)
        elif SIEVE_BEFORE_RECONCILE_MARK in line:
            reconcile = parse_reconcile(line)
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
            if (not compress_trivial_reconcile) or (
                compress_trivial_reconcile
                and not cur_reconcile_is_trivial[controller_name]
            ):
                # When compress_trivial_reconcile is disabled, we directly set prev_reconcile_start_timestamp
                # When compress_trivial_reconcile is enabled, we do not set prev_reconcile_start_timestamp
                # if no side effects happen during the last reconcile
                prev_reconcile_start_timestamp[
                    controller_name
                ] = cur_reconcile_start_timestamp[controller_name]
            cur_reconcile_start_timestamp[controller_name] = i
            # Reset cur_reconcile_is_trivial[controller_name] to True as a new round of reconcile just starts
            cur_reconcile_is_trivial[controller_name] = True
        elif SIEVE_AFTER_RECONCILE_MARK in line:
            reconcile = parse_reconcile(line)
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
        if SIEVE_BEFORE_SIDE_EFFECT_MARK in line:
            side_effect_id = parse_side_effect_id_only(line)
            if side_effect_id.id in side_effect_id_map:
                side_effect_list.append(side_effect_id_map[side_effect_id.id])
    return side_effect_list


def extract_events_and_effects(path, compress_trivial_reconcile):
    event_list = parse_events(path)
    side_effect_list = parse_side_effects(path, compress_trivial_reconcile)
    return event_list, side_effect_list


def base_pass(
    event_vertices: List[CausalityVertex], side_effect_vertices: List[CausalityVertex]
):
    print("Running base pass ...")
    vertex_pairs = []
    for side_effect_vertex in side_effect_vertices:
        for event_vertex in event_vertices:
            # events can lead to that side_effect
            if side_effect_vertex.content.range_overlap(event_vertex.content):
                vertex_pairs.append([event_vertex, side_effect_vertex])
    return vertex_pairs


def write_read_overlap_filtering_pass(vertex_pairs: List[List[CausalityVertex]]):
    print("Running optional pass: write-read-overlap-filtering ...")
    pruned_vertex_pairs = []
    for pair in vertex_pairs:
        event_vertex = pair[0]
        side_effect_vertex = pair[1]
        if side_effect_vertex.content.interest_overlap(event_vertex.content):
            pruned_vertex_pairs.append(pair)
    print("<e, s> pairs: %d -> %d" % (len(vertex_pairs), len(pruned_vertex_pairs)))
    return pruned_vertex_pairs


def error_msg_filtering_pass(vertex_pairs: List[List[CausalityVertex]]):
    print("Running optional pass: error-message-filtering ...")
    pruned_vertex_pairs = []
    for pair in vertex_pairs:
        side_effect_vertex = pair[1]
        if side_effect_vertex.content.error in ALLOWED_ERROR_TYPE:
            pruned_vertex_pairs.append(pair)
    print("<e, s> pairs: %d -> %d" % (len(vertex_pairs), len(pruned_vertex_pairs)))
    return pruned_vertex_pairs


def generate_event_effect_pairs(causality_graph: CausalityGraph):
    event_vertices = causality_graph.event_vertices
    side_effect_vertices = causality_graph.side_effect_vertices
    vertex_pairs = base_pass(event_vertices, side_effect_vertices)
    if ERROR_MSG_FILTER_FLAG:
        vertex_pairs = error_msg_filtering_pass(vertex_pairs)
    if WRITE_READ_FILTER_FLAG:
        vertex_pairs = write_read_overlap_filtering_pass(vertex_pairs)
    return vertex_pairs


def generate_effect_event_pairs(causality_graph: CausalityGraph):
    vertex_pairs = []
    event_vertices = causality_graph.event_vertices
    side_effect_vertices = causality_graph.side_effect_vertices
    event_key_map = causality_graph.event_key_to_event_vertices
    for side_effect_vertex in side_effect_vertices:
        if side_effect_vertex.content.key in event_key_map:
            for event_vertex in event_vertices:
                if (
                    event_vertex.content.obj_str == side_effect_vertex.content.obj_str
                    and side_effect_vertex.content.start_timestamp
                    < event_vertex.content.start_timestamp
                    and consistent_type(
                        event_vertex.content.etype, side_effect_vertex.content.etype
                    )
                ):
                    vertex_pairs.append([side_effect_vertex, event_vertex])
                    break
    return vertex_pairs


def build_causality_graph(event_list, side_effect_list):
    causality_graph = CausalityGraph()
    causality_graph.add_sorted_events(event_list)
    causality_graph.add_sorted_side_effects(side_effect_list)

    event_effect_pairs = generate_event_effect_pairs(causality_graph)
    effect_event_pairs = generate_effect_event_pairs(causality_graph)

    for pair in event_effect_pairs:
        causality_graph.connect_event_to_side_effect(pair[0], pair[1])

    for pair in effect_event_pairs:
        causality_graph.connect_side_effect_to_event(pair[0], pair[1])

    causality_graph.finalize()
    causality_graph.sanity_check()

    return causality_graph


def generate_test_config(analysis_mode, project, log_dir, two_sided, causality_graph):
    generated_config_dir = os.path.join(log_dir, analysis_mode)
    if os.path.isdir(generated_config_dir):
        shutil.rmtree(generated_config_dir)
    os.makedirs(generated_config_dir, exist_ok=True)
    if analysis_mode == sieve_modes.TIME_TRAVEL:
        analyze_gen.time_travel_analysis(causality_graph, generated_config_dir, project)
        if two_sided:
            analyze_gen.time_travel_analysis(
                causality_graph,
                generated_config_dir,
                project,
                "before",
            )
    elif analysis_mode == sieve_modes.OBS_GAP:
        analyze_gen.obs_gap_analysis(causality_graph, generated_config_dir, project)
    elif analysis_mode == sieve_modes.ATOM_VIO:
        analyze_gen.atom_vio_analysis(causality_graph, generated_config_dir, project)


def analyze_trace(
    project,
    log_dir,
    generate_oracle=True,
    generate_config=True,
    two_sided=False,
    use_sql=False,
    compress_trivial_reconcile=True,
):
    print(
        "generate-oracle feature is %s" % ("enabled" if generate_oracle else "disabled")
    )
    print(
        "generate-config feature is %s" % ("enabled" if generate_config else "disabled")
    )
    if not generate_config:
        two_sided = False
        use_sql = False
    print("two-sided feature is %s" % ("enabled" if two_sided else "disabled"))
    print("use-sql feature is %s" % ("enabled" if use_sql else "disabled"))

    log_path = os.path.join(log_dir, "sieve-server.log")
    print("Sanity checking the sieve log %s ..." % log_path)
    sanity_check_sieve_log(log_path)
    event_list, side_effect_list = extract_events_and_effects(
        log_path, compress_trivial_reconcile
    )
    causality_graph = build_causality_graph(event_list, side_effect_list)

    if generate_config:
        for analysis_mode in [
            sieve_modes.TIME_TRAVEL,
            sieve_modes.OBS_GAP,
            sieve_modes.ATOM_VIO,
        ]:
            generate_test_config(
                analysis_mode, project, log_dir, two_sided, causality_graph
            )

    if generate_oracle:
        oracle.generate_test_oracle(log_dir)


if __name__ == "__main__":
    usage = "usage: python3 analyze.py [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option(
        "-p",
        "--project",
        dest="project",
        help="specify PROJECT",
        metavar="PROJECT",
        default="cassandra-operator",
    )
    parser.add_option(
        "-t",
        "--test",
        dest="test",
        help="specify TEST to run",
        metavar="TEST",
        default="recreate",
    )
    (options, args) = parser.parse_args()
    project = options.project
    test = options.test
    print("Analyzing controller trace for %s's test workload %s ..." % (project, test))
    # hardcoded to time travel config only for now
    dir = os.path.join("log", project, test, "learn", "learn")
    analyze_trace(
        project,
        dir,
        generate_oracle=False,
        generate_config=True,
        two_sided=False,
        use_sql=False,
        compress_trivial_reconcile=True,
    )
