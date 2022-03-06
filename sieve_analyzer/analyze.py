import copy
import os
import shutil
from typing import List
from sieve_common.common import (
    TestContext,
    fail,
    sieve_built_in_test_patterns,
)
from sieve_perturbation_policies.intermediate_state import intermediate_state_analysis
from sieve_perturbation_policies.stale_state import stale_state_analysis
from sieve_perturbation_policies.unobserved_state import unobserved_state_analysis
from sieve_common.k8s_event import *
from sieve_analyzer.event_graph import (
    EventGraph,
    EventVertex,
)


def sanity_check_sieve_log(path):
    lines = open(path).readlines()
    reconcile_status = {}
    operator_write_status = {}
    operator_hear_status = {}
    for i in range(len(lines)):
        line = lines[i]
        if SIEVE_BEFORE_WRITE_MARK in line:
            operator_write_id = parse_operator_write_id_only(line).id
            assert operator_write_id not in operator_write_status, line
            operator_write_status[operator_write_id] = 1
        elif SIEVE_AFTER_WRITE_MARK in line:
            operator_write_id = parse_operator_write_id_only(line).id
            assert operator_write_id in operator_write_status, line
            operator_write_status[operator_write_id] += 1
        elif SIEVE_BEFORE_HEAR_MARK in line:
            operator_hear_id = parse_operator_hear_id_only(line).id
            assert operator_hear_id not in operator_hear_status, line
            operator_hear_status[operator_hear_id] = 1
        elif SIEVE_AFTER_HEAR_MARK in line:
            operator_hear_id = parse_operator_hear_id_only(line).id
            assert operator_hear_id in operator_hear_status, line
            operator_hear_status[operator_hear_id] += 1
        elif SIEVE_BEFORE_RECONCILE_MARK in line:
            reconciler_type = parse_reconcile(line).reconciler_type
            if reconciler_type not in reconcile_status:
                reconcile_status[reconciler_type] = 0
            reconcile_status[reconciler_type] += 1
            assert reconcile_status[reconciler_type] == 1, line
        elif SIEVE_AFTER_RECONCILE_MARK in line:
            reconciler_type = parse_reconcile(line).reconciler_type
            assert reconciler_type in reconcile_status, line
            reconcile_status[reconciler_type] -= 1
            assert reconcile_status[reconciler_type] == 0, line
    for key in operator_write_status:
        assert operator_write_status[key] == 1 or operator_write_status[key] == 2
    for key in operator_hear_status:
        assert operator_hear_status[key] == 1 or operator_hear_status[key] == 2
    for key in reconcile_status:
        assert (
            reconcile_status[reconciler_type] == 0
            or reconcile_status[reconciler_type] == 1
        )


def parse_receiver_events(path):
    # { operator_hear id -> operator_hear }
    operator_hear_id_map = {}
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
    return operator_hear_list


def parse_reconciler_events(test_context: TestContext, path):
    operator_write_start_timestamp_map = {}
    operator_nk_write_start_timestamp_map = {}
    read_types_this_reconcile = set()
    read_keys_this_reconcile = set()
    prev_reconcile_per_type = {}
    cur_reconcile_per_type = {}
    cur_reconcile_is_trivial = {}
    ts_to_event_map = {}
    # there could be multiple controllers running concurrently
    # we need to record all the ongoing controllers
    # there could be multiple workers running for a single controller
    # so we need to count each worker for each controller
    # ongoing_reconcile = { reconciler_type -> number of ongoing workers for this controller }
    ongoing_reconciles = {}
    lines = open(path).readlines()
    for i in range(len(lines)):
        line = lines[i]
        if SIEVE_BEFORE_WRITE_MARK in line:
            operator_write_id_only = parse_operator_write_id_only(line)
            operator_write_start_timestamp_map[operator_write_id_only.id] = i
        elif SIEVE_AFTER_WRITE_MARK in line:
            for key in cur_reconcile_is_trivial:
                cur_reconcile_is_trivial[key] = False
            # If we have not met any reconcile yet, skip the operator_write since it is not caused by reconcile
            # though it should not happen at all.
            # TODO: handle the writes that are not in any reconcile
            operator_write = parse_operator_write(line)
            if operator_write.reconciler_type not in cur_reconcile_per_type:
                if not test_context.controller_config.loosen_reconciler_boundary:
                    continue
            # Do deepcopy here to ensure the later changes to the two sets
            # will not affect this operator_write.
            # cache read during that possible interval
            operator_write.read_keys = copy.deepcopy(read_keys_this_reconcile)
            operator_write.read_types = copy.deepcopy(read_types_this_reconcile)
            operator_write.start_timestamp = operator_write_start_timestamp_map[
                operator_write.id
            ]
            operator_write.end_timestamp = i
            if operator_write.reconciler_type in cur_reconcile_per_type:
                prev_reconcile = prev_reconcile_per_type[operator_write.reconciler_type]
                cur_reconcile = cur_reconcile_per_type[operator_write.reconciler_type]
                earliest_timestamp = -1
                if prev_reconcile is not None:
                    earliest_timestamp = prev_reconcile.end_timestamp
                operator_write.set_range(earliest_timestamp, i)
                operator_write.reconcile_id = cur_reconcile.reconcile_id
            ts_to_event_map[operator_write.start_timestamp] = operator_write
        elif SIEVE_BEFORE_ANNOTATED_API_INVOCATION_MARK in line:
            id_only = parse_operator_non_k8s_write_id_only(line)
            operator_nk_write_start_timestamp_map[id_only.id] = i
        elif SIEVE_AFTER_ANNOTATED_API_INVOCATION_MARK in line:
            for key in cur_reconcile_is_trivial:
                cur_reconcile_is_trivial[key] = False
            operator_nk_write = parse_operator_non_k8s_write(line)
            if operator_nk_write.reconciler_type not in cur_reconcile_per_type:
                if not test_context.controller_config.loosen_reconciler_boundary:
                    continue
            operator_nk_write.start_timestamp = operator_nk_write_start_timestamp_map[
                operator_nk_write.id
            ]
            operator_nk_write.end_timestamp = i
            if operator_nk_write.reconciler_type in cur_reconcile_per_type:
                prev_reconcile = prev_reconcile_per_type[
                    operator_nk_write.reconciler_type
                ]
                cur_reconcile = cur_reconcile_per_type[
                    operator_nk_write.reconciler_type
                ]
                earliest_timestamp = -1
                if prev_reconcile is not None:
                    earliest_timestamp = prev_reconcile.end_timestamp
                operator_nk_write.set_range(earliest_timestamp, i)
                operator_nk_write.reconcile_id = cur_reconcile.reconcile_id
            ts_to_event_map[operator_nk_write.start_timestamp] = operator_nk_write
            print("nk write end")
        elif SIEVE_AFTER_READ_MARK in line:
            # TODO: handle the reads that are not in any reconcile
            operator_read = parse_operator_read(line)
            if operator_read.reconciler_type not in cur_reconcile_per_type:
                continue
            operator_read.end_timestamp = i
            cur_reconcile = cur_reconcile_per_type[operator_read.reconciler_type]
            operator_read.reconcile_id = cur_reconcile.reconcile_id
            ts_to_event_map[operator_read.end_timestamp] = operator_read
            if operator_read.etype == "Get":
                read_keys_this_reconcile.update(operator_read.key_set)
            else:
                read_types_this_reconcile.add(operator_read.rtype)
        elif SIEVE_BEFORE_RECONCILE_MARK in line:
            reconcile_begin = parse_reconcile(line)
            reconcile_begin.end_timestamp = i
            ts_to_event_map[reconcile_begin.end_timestamp] = reconcile_begin
            reconciler_type = reconcile_begin.reconciler_type
            if reconciler_type not in ongoing_reconciles:
                ongoing_reconciles[reconciler_type] = 1
            else:
                ongoing_reconciles[reconciler_type] += 1
            # let's assume there should be only one worker for each controller here
            assert ongoing_reconciles[reconciler_type] == 1
            if reconciler_type not in cur_reconcile_per_type:
                prev_reconcile_per_type[reconciler_type] = None
                cur_reconcile_per_type[reconciler_type] = reconcile_begin
            else:
                if not test_context.common_config.compress_trivial_reconcile_enabled:
                    prev_reconcile_per_type[reconciler_type] = cur_reconcile_per_type[
                        reconciler_type
                    ]
                    cur_reconcile_per_type[reconciler_type] = reconcile_begin
                elif (
                    test_context.common_config.compress_trivial_reconcile_enabled
                    and not cur_reconcile_is_trivial[reconciler_type]
                ):
                    prev_reconcile_per_type[reconciler_type] = cur_reconcile_per_type[
                        reconciler_type
                    ]
                    cur_reconcile_per_type[reconciler_type] = reconcile_begin
            cur_reconcile_is_trivial[reconciler_type] = True
        elif SIEVE_AFTER_RECONCILE_MARK in line:
            reconcile_end = parse_reconcile(line)
            reconcile_end.end_timestamp = i
            ts_to_event_map[reconcile_end.end_timestamp] = reconcile_end
            reconciler_type = reconcile_end.reconciler_type
            ongoing_reconciles[reconciler_type] -= 1
            if ongoing_reconciles[reconciler_type] == 0:
                del ongoing_reconciles[reconciler_type]
            # Clear the read keys and types set since all the ongoing reconciles are done
            if len(ongoing_reconciles) == 0:
                read_keys_this_reconcile = set()
                read_types_this_reconcile = set()
    reconciler_event_list = [event for ts, event in sorted(ts_to_event_map.items())]
    return reconciler_event_list


def base_pass(
    operator_hear_vertices: List[EventVertex],
    operator_write_vertices: List[EventVertex],
    operator_non_k8s_write_vertices: List[EventVertex],
):
    print("Running base pass...")
    vertex_pairs = []
    write_vertices = operator_write_vertices + operator_non_k8s_write_vertices
    for operator_write_vertex in write_vertices:
        for operator_hear_vertex in operator_hear_vertices:
            if operator_write_vertex.content.reconcile_id == -1:
                continue
            # operator_hears can lead to that operator_write
            hear_within_reconcile_scope = (
                operator_write_vertex.content.range_start_timestamp
                < operator_hear_vertex.content.end_timestamp
            )
            write_after_hear = (
                operator_write_vertex.content.start_timestamp
                > operator_hear_vertex.content.start_timestamp
            )
            if hear_within_reconcile_scope and write_after_hear:
                vertex_pairs.append([operator_hear_vertex, operator_write_vertex])
    return vertex_pairs


def hear_read_overlap_filtering_pass(vertex_pairs: List[List[EventVertex]]):
    print("Running optional pass: hear-read-overlap-filtering...")
    pruned_vertex_pairs = []
    for pair in vertex_pairs:
        operator_hear_vertex = pair[0]
        operator_write_vertex = pair[1]
        if operator_write_vertex.is_operator_write():
            key_match = (
                operator_hear_vertex.content.key
                in operator_write_vertex.content.read_keys
            )
            type_match = (
                operator_hear_vertex.content.rtype
                in operator_write_vertex.content.read_types
            )
            if key_match or type_match:
                pruned_vertex_pairs.append(pair)
        else:
            pruned_vertex_pairs.append(pair)
    print("<e, s> pairs: %d -> %d" % (len(vertex_pairs), len(pruned_vertex_pairs)))
    return pruned_vertex_pairs


def error_msg_filtering_pass(vertex_pairs: List[List[EventVertex]]):
    print("Running optional pass: error-message-filtering...")
    pruned_vertex_pairs = []
    for pair in vertex_pairs:
        operator_write_vertex = pair[1]
        if operator_write_vertex.is_operator_write():
            if operator_write_vertex.content.error in ALLOWED_ERROR_TYPE:
                pruned_vertex_pairs.append(pair)
        else:
            pruned_vertex_pairs.append(pair)
    print("<e, s> pairs: %d -> %d" % (len(vertex_pairs), len(pruned_vertex_pairs)))
    return pruned_vertex_pairs


def generate_hear_write_pairs(event_graph: EventGraph):
    operator_hear_vertices = event_graph.operator_hear_vertices
    operator_write_vertices = event_graph.operator_write_vertices
    operator_non_k8s_write_vertices = event_graph.operator_non_k8s_write_vertices
    vertex_pairs = base_pass(
        operator_hear_vertices, operator_write_vertices, operator_non_k8s_write_vertices
    )
    if HEAR_READ_FILTER_FLAG:
        vertex_pairs = hear_read_overlap_filtering_pass(vertex_pairs)
    return vertex_pairs


def generate_write_hear_pairs(event_graph: EventGraph):
    vertex_pairs = []
    operator_hear_vertices = event_graph.operator_hear_vertices
    operator_write_vertices = event_graph.operator_write_vertices
    operator_hear_key_map = event_graph.operator_hear_key_to_vertices
    for operator_write_vertex in operator_write_vertices:
        if operator_write_vertex.content.key in operator_hear_key_map:
            for operator_hear_vertex in operator_hear_vertices:
                if (
                    operator_hear_vertex.content.obj_str
                    == operator_write_vertex.content.obj_str
                    and operator_write_vertex.content.start_timestamp
                    < operator_hear_vertex.content.start_timestamp
                    and consistent_event_type(
                        operator_hear_vertex.content.etype,
                        operator_write_vertex.content.etype,
                    )
                ):
                    vertex_pairs.append([operator_write_vertex, operator_hear_vertex])
                    break
    return vertex_pairs


def build_event_graph(test_context: TestContext, log_path, oracle_dir):
    learned_masked_paths = json.load(open(os.path.join(oracle_dir, "mask.json")))

    operator_hear_list = parse_receiver_events(log_path)
    reconciler_event_list = parse_reconciler_events(test_context, log_path)

    event_graph = EventGraph(
        learned_masked_paths,
        test_context.common_config.field_key_mask,
        test_context.common_config.field_path_mask,
    )
    event_graph.add_sorted_operator_hears(operator_hear_list)
    event_graph.add_sorted_reconciler_events(reconciler_event_list)

    hear_write_pairs = generate_hear_write_pairs(event_graph)
    # write_hear_pairs = generate_write_hear_pairs(event_graph)

    for pair in hear_write_pairs:
        event_graph.connect_hear_to_write(pair[0], pair[1])

    # for pair in write_hear_pairs:
    #     event_graph.connect_write_to_hear(pair[0], pair[1])

    event_graph.finalize()
    event_graph.sanity_check()

    return event_graph


def generate_test_config(
    test_context: TestContext, analysis_mode, event_graph: EventGraph
):
    log_dir = test_context.result_dir
    generated_config_dir = os.path.join(log_dir, analysis_mode)
    if os.path.isdir(generated_config_dir):
        shutil.rmtree(generated_config_dir)
    os.makedirs(generated_config_dir, exist_ok=True)
    if analysis_mode == sieve_built_in_test_patterns.STALE_STATE:
        return stale_state_analysis(event_graph, generated_config_dir, test_context)
    elif analysis_mode == sieve_built_in_test_patterns.UNOBSERVED_STATE:
        return unobserved_state_analysis(
            event_graph, generated_config_dir, test_context
        )
    elif analysis_mode == sieve_built_in_test_patterns.INTERMEDIATE_STATE:
        return intermediate_state_analysis(
            event_graph, generated_config_dir, test_context
        )


def analyze_trace(
    test_context: TestContext,
):
    log_dir = test_context.result_dir
    oracle_dir = test_context.oracle_dir

    log_path = os.path.join(log_dir, "sieve-server.log")
    print("Sanity checking the sieve log %s..." % log_path)
    sanity_check_sieve_log(log_path)

    if not os.path.exists(os.path.join(oracle_dir, "mask.json")):
        fail("cannot find mask.json")
        return
    event_graph = build_event_graph(test_context, log_path, oracle_dir)
    sieve_learn_result = {
        "project": test_context.project,
        "test": test_context.test_name,
    }
    for analysis_mode in [
        sieve_built_in_test_patterns.STALE_STATE,
        sieve_built_in_test_patterns.UNOBSERVED_STATE,
        sieve_built_in_test_patterns.INTERMEDIATE_STATE,
    ]:
        (
            baseline_spec_number,
            after_p1_spec_number,
            after_p2_spec_number,
            final_spec_number,
        ) = generate_test_config(test_context, analysis_mode, event_graph)
        sieve_learn_result[analysis_mode] = {
            "baseline": baseline_spec_number,
            "after_p1": after_p1_spec_number,
            "after_p2": after_p2_spec_number,
            "final": final_spec_number,
        }

    result_filename = "sieve_learn_results/{}-{}.json".format(
        test_context.project, test_context.test_name
    )
    os.makedirs("sieve_learn_results", exist_ok=True)
    with open(result_filename, "w") as test_result_json:
        json.dump(
            sieve_learn_result,
            test_result_json,
            indent=4,
        )
