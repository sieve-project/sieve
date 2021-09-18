from analyze_event import cancel_event_object, canonicalize_event_object, diff_events
from typing import List
import copy
import os
from analyze_util import *
import oracle
import shutil
import optparse
import analyze_gen
from common import sieve_modes, sieve_stages


def sanity_check_sieve_log(path):
    lines = open(path).readlines()
    reconcile_status = {}
    operator_write_status = {}
    operator_hear_status = {}
    for i in range(len(lines)):
        line = lines[i]
        if SIEVE_BEFORE_WRITE_MARK in line:
            operator_write_id = parse_operator_write_id_only(line).id
            assert operator_write_id not in operator_write_status
            operator_write_status[operator_write_id] = 1
        elif SIEVE_AFTER_WRITE_MARK in line:
            operator_write_id = parse_operator_write_id_only(line).id
            assert operator_write_id in operator_write_status
            operator_write_status[operator_write_id] += 1
        elif SIEVE_BEFORE_HEAR_MARK in line:
            operator_hear_id = parse_operator_hear_id_only(line).id
            assert operator_hear_id not in operator_hear_status
            operator_hear_status[operator_hear_id] = 1
        elif SIEVE_AFTER_HEAR_MARK in line:
            operator_hear_id = parse_operator_hear_id_only(line).id
            assert operator_hear_id in operator_hear_status
            operator_hear_status[operator_hear_id] += 1
        elif SIEVE_BEFORE_RECONCILE_MARK in line:
            reconcile_id = parse_reconcile(line).controller_name
            if reconcile_id not in reconcile_status:
                reconcile_status[reconcile_id] = 0
            reconcile_status[reconcile_id] += 1
            assert reconcile_status[reconcile_id] == 1
        elif SIEVE_AFTER_RECONCILE_MARK in line:
            reconcile_id = parse_reconcile(line).controller_name
            assert reconcile_id in reconcile_status
            reconcile_status[reconcile_id] -= 1
            assert reconcile_status[reconcile_id] == 0
    for key in operator_write_status:
        assert operator_write_status[key] == 1 or operator_write_status[key] == 2
    for key in operator_hear_status:
        assert operator_hear_status[key] == 1 or operator_hear_status[key] == 2
    for key in reconcile_status:
        assert (
            reconcile_status[reconcile_id] == 0 or reconcile_status[reconcile_id] == 1
        )


def parse_operator_hears(path):
    # { operator_hear id -> operator_hear }
    operator_hear_id_map = {}
    # { operator_hear key -> [operator_hears belonging to the key] }
    operator_hear_key_map = {}
    # we need this map to later find the previous operator_hear for each crucial operator_hear
    operator_hear_list = []
    lines = open(path).readlines()
    largest_timestamp = len(lines)
    for i in range(len(lines)):
        line = lines[i]
        if SIEVE_BEFORE_HEAR_MARK in line:
            operator_hear = parse_operator_hear(line)
            operator_hear.start_timestamp = i
            # We initially set the operator_hear end time as the largest timestamp
            # so that if we never meet SIEVE_AFTER_HEAR_MARK for this operator_hear,
            # we will not pose any constraint on its end time in range_overlap
            operator_hear.end_timestamp = largest_timestamp
            operator_hear_id_map[operator_hear.id] = operator_hear
        elif SIEVE_AFTER_HEAR_MARK in line:
            operator_hear_id_only = parse_operator_hear_id_only(line)
            operator_hear_id_map[operator_hear_id_only.id].end_timestamp = i
    for i in range(len(lines)):
        line = lines[i]
        if SIEVE_BEFORE_HEAR_MARK in line:
            operator_hear = parse_operator_hear(line)
            operator_hear_list.append(operator_hear_id_map[operator_hear.id])
            if operator_hear.key not in operator_hear_key_map:
                operator_hear_key_map[operator_hear.key] = []
            operator_hear_key_map[operator_hear.key].append(
                operator_hear_id_map[operator_hear.id]
            )
    for key in operator_hear_key_map:
        for i in range(len(operator_hear_key_map[key])):
            if i == 0:
                continue
            prev_operator_hear = operator_hear_key_map[key][i - 1]
            cur_operator_hear = operator_hear_key_map[key][i]
            canonicalized_prev_object = canonicalize_event_object(
                copy.deepcopy(prev_operator_hear.obj_map)
            )
            canonicalized_cur_object = canonicalize_event_object(
                copy.deepcopy(cur_operator_hear.obj_map)
            )
            slim_prev_object, slim_cur_object = diff_events(
                canonicalized_prev_object, canonicalized_cur_object
            )
            cur_operator_hear.slim_prev_obj_map = slim_prev_object
            cur_operator_hear.slim_cur_obj_map = slim_cur_object
            cur_operator_hear.prev_etype = prev_operator_hear.etype
    for key in operator_hear_key_map:
        for i in range(len(operator_hear_key_map[key]) - 1):
            cancelled_by = set()
            cur_operator_hear = operator_hear_key_map[key][i]
            for j in range(i + 1, len(operator_hear_key_map[key])):
                following_operator_hear = operator_hear_key_map[key][j]
                if i == 0:
                    cancelled_by.add(following_operator_hear.id)
                    continue
                if (
                    cur_operator_hear.etype != OperatorHearTypes.DELETED
                    and following_operator_hear.etype != OperatorHearTypes.DELETED
                    and cancel_event_object(
                        cur_operator_hear.slim_cur_obj_map,
                        following_operator_hear.obj_map,
                    )
                    or (
                        cur_operator_hear.etype != OperatorHearTypes.DELETED
                        and following_operator_hear.etype == OperatorHearTypes.DELETED
                    )
                    or (
                        cur_operator_hear.etype == OperatorHearTypes.DELETED
                        and following_operator_hear.etype != OperatorHearTypes.DELETED
                    )
                ):
                    cancelled_by.add(following_operator_hear.id)
            cur_operator_hear.cancelled_by = cancelled_by
    return operator_hear_list


def parse_operator_writes(path, compress_trivial_reconcile=True):
    operator_write_id_map = {}
    operator_write_list = []
    operator_write_id_to_start_ts_map = {}
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
        if SIEVE_BEFORE_WRITE_MARK in line:
            operator_write_id_only = parse_operator_write_id_only(line)
            operator_write_id_to_start_ts_map[operator_write_id_only.id] = i
        if SIEVE_AFTER_WRITE_MARK in line:
            for key in cur_reconcile_is_trivial:
                cur_reconcile_is_trivial[key] = False
            # If we have not met any reconcile yet, skip the operator_write since it is not caused by reconcile
            # though it should not happen at all.
            if len(ongoing_reconciles) == 0:
                continue
            operator_write = parse_operator_write(line)
            # Do deepcopy here to ensure the later changes to the two sets
            # will not affect this operator_write.
            # cache read during that possible interval
            operator_write.read_keys = copy.deepcopy(read_keys_this_reconcile)
            operator_write.read_types = copy.deepcopy(read_types_this_reconcile)
            operator_write.start_timestamp = operator_write_id_to_start_ts_map[
                operator_write.id
            ]
            operator_write.end_timestamp = i
            # We want to find the earilest timestamp before which any operator_hear will not affect the operator_write.
            # The earlies timestamp should be min(the timestamp of the previous reconcile start of all ongoing reconiles).
            # One special case is that at least one of the ongoing reconcile is the first reconcile of that controller.
            # In that case we will use -1 as the earliest timestamp:
            # we do not pose constraint on operator_hear end time in range_overlap.
            earliest_timestamp = i
            for controller_name in ongoing_reconciles:
                if prev_reconcile_start_timestamp[controller_name] < earliest_timestamp:
                    earliest_timestamp = prev_reconcile_start_timestamp[controller_name]
            operator_write.set_range(earliest_timestamp, i)
            operator_write_id_map[operator_write.id] = operator_write
        elif SIEVE_AFTER_READ_MARK in line:
            cache_read = parse_cache_read(line)
            if cache_read.etype == "Get":
                read_keys_this_reconcile.update(cache_read.key_set)
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
                # if no operator_writes happen during the last reconcile
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
        if SIEVE_BEFORE_WRITE_MARK in line:
            operator_write_id = parse_operator_write_id_only(line)
            if operator_write_id.id in operator_write_id_map:
                operator_write_list.append(operator_write_id_map[operator_write_id.id])
    return operator_write_list


def extract_operator_hears_and_operator_writes(path, compress_trivial_reconcile):
    operator_hear_list = parse_operator_hears(path)
    operator_write_list = parse_operator_writes(path, compress_trivial_reconcile)
    return operator_hear_list, operator_write_list


def base_pass(
    operator_hear_vertices: List[CausalityVertex],
    operator_write_vertices: List[CausalityVertex],
):
    print("Running base pass ...")
    vertex_pairs = []
    for operator_write_vertex in operator_write_vertices:
        for operator_hear_vertex in operator_hear_vertices:
            # operator_hears can lead to that operator_write
            if range_overlap(
                operator_write_vertex.content, operator_hear_vertex.content
            ):
                vertex_pairs.append([operator_hear_vertex, operator_write_vertex])
    return vertex_pairs


def hear_read_overlap_filtering_pass(vertex_pairs: List[List[CausalityVertex]]):
    print("Running optional pass: hear-read-overlap-filtering ...")
    pruned_vertex_pairs = []
    for pair in vertex_pairs:
        operator_hear_vertex = pair[0]
        operator_write_vertex = pair[1]
        if interest_overlap(
            operator_write_vertex.content, operator_hear_vertex.content
        ):
            pruned_vertex_pairs.append(pair)
    print("<e, s> pairs: %d -> %d" % (len(vertex_pairs), len(pruned_vertex_pairs)))
    return pruned_vertex_pairs


def error_msg_filtering_pass(vertex_pairs: List[List[CausalityVertex]]):
    print("Running optional pass: error-message-filtering ...")
    pruned_vertex_pairs = []
    for pair in vertex_pairs:
        operator_write_vertex = pair[1]
        if operator_write_vertex.content.error in ALLOWED_ERROR_TYPE:
            pruned_vertex_pairs.append(pair)
    print("<e, s> pairs: %d -> %d" % (len(vertex_pairs), len(pruned_vertex_pairs)))
    return pruned_vertex_pairs


def generate_hear_write_pairs(causality_graph: CausalityGraph):
    operator_hear_vertices = causality_graph.operator_hear_vertices
    operator_write_vertices = causality_graph.operator_write_vertices
    vertex_pairs = base_pass(operator_hear_vertices, operator_write_vertices)
    if ERROR_MSG_FILTER_FLAG:
        vertex_pairs = error_msg_filtering_pass(vertex_pairs)
    if HEAR_READ_FILTER_FLAG:
        vertex_pairs = hear_read_overlap_filtering_pass(vertex_pairs)
    return vertex_pairs


def generate_write_hear_pairs(causality_graph: CausalityGraph):
    vertex_pairs = []
    operator_hear_vertices = causality_graph.operator_hear_vertices
    operator_write_vertices = causality_graph.operator_write_vertices
    operator_hear_key_map = causality_graph.operator_hear_key_to_operator_hear_vertices
    for operator_write_vertex in operator_write_vertices:
        if operator_write_vertex.content.key in operator_hear_key_map:
            for operator_hear_vertex in operator_hear_vertices:
                if (
                    operator_hear_vertex.content.obj_str
                    == operator_write_vertex.content.obj_str
                    and operator_write_vertex.content.start_timestamp
                    < operator_hear_vertex.content.start_timestamp
                    and consistent_type(
                        operator_hear_vertex.content.etype,
                        operator_write_vertex.content.etype,
                    )
                ):
                    vertex_pairs.append([operator_write_vertex, operator_hear_vertex])
                    break
    return vertex_pairs


def build_causality_graph(operator_hear_list, operator_write_list):
    causality_graph = CausalityGraph()
    causality_graph.add_sorted_operator_hears(operator_hear_list)
    causality_graph.add_sorted_operator_writes(operator_write_list)

    hear_write_pairs = generate_hear_write_pairs(causality_graph)
    write_hear_pairs = generate_write_hear_pairs(causality_graph)

    for pair in hear_write_pairs:
        causality_graph.connect_operator_hear_to_operator_write(pair[0], pair[1])

    for pair in write_hear_pairs:
        causality_graph.connect_operator_write_to_operator_hear(pair[0], pair[1])

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
    data_dir,
    generate_oracle=True,
    generate_config=True,
    two_sided=False,
    use_sql=False,
    compress_trivial_reconcile=True,
    canonicalize_resource=False,
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
    (
        operator_hear_list,
        operator_write_list,
    ) = extract_operator_hears_and_operator_writes(log_path, compress_trivial_reconcile)
    causality_graph = build_causality_graph(operator_hear_list, operator_write_list)

    if generate_config and not canonicalize_resource:
        for analysis_mode in [
            sieve_modes.TIME_TRAVEL,
            sieve_modes.OBS_GAP,
            sieve_modes.ATOM_VIO,
        ]:
            generate_test_config(
                analysis_mode, project, log_dir, two_sided, causality_graph
            )

    if generate_oracle:
        oracle.generate_test_oracle(log_dir, canonicalize_resource)


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
    dir = os.path.join("log", project, test, sieve_stages.LEARN, sieve_modes.LEARN_ONCE)
    analyze_trace(
        project,
        dir,
        "",
        generate_oracle=False,
        generate_config=True,
        two_sided=False,
        use_sql=False,
        compress_trivial_reconcile=True,
    )
