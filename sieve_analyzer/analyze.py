import copy
import os
from typing import List
from sieve_common.common import (
    TestContext,
    fail,
    sieve_built_in_test_patterns,
    rmtree_if_exists,
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
    controller_write_status = {}
    controller_hear_status = {}
    for i in range(len(lines)):
        line = lines[i]
        if SIEVE_BEFORE_REST_WRITE_MARK in line:
            controller_write_id = parse_controller_write_id_only(line).id
            assert controller_write_id not in controller_write_status, line
            controller_write_status[controller_write_id] = 1
        elif SIEVE_AFTER_REST_WRITE_MARK in line:
            controller_write_id = parse_controller_write_id_only(line).id
            assert controller_write_id in controller_write_status, line
            controller_write_status[controller_write_id] += 1
        elif SIEVE_BEFORE_HEAR_MARK in line:
            controller_hear_id = parse_controller_hear_id_only(line).id
            assert controller_hear_id not in controller_hear_status, line
            controller_hear_status[controller_hear_id] = 1
        elif SIEVE_AFTER_HEAR_MARK in line:
            controller_hear_id = parse_controller_hear_id_only(line).id
            assert controller_hear_id in controller_hear_status, line
            controller_hear_status[controller_hear_id] += 1
        elif SIEVE_BEFORE_RECONCILE_MARK in line:
            reconcile_fun = parse_reconcile(line).reconcile_fun
            if reconcile_fun not in reconcile_status:
                reconcile_status[reconcile_fun] = 0
            reconcile_status[reconcile_fun] += 1
            assert reconcile_status[reconcile_fun] == 1, line
        elif SIEVE_AFTER_RECONCILE_MARK in line:
            reconcile_fun = parse_reconcile(line).reconcile_fun
            assert reconcile_fun in reconcile_status, line
            reconcile_status[reconcile_fun] -= 1
            assert reconcile_status[reconcile_fun] == 0, line
    for key in controller_write_status:
        assert controller_write_status[key] == 1 or controller_write_status[key] == 2
    for key in controller_hear_status:
        assert controller_hear_status[key] == 1 or controller_hear_status[key] == 2
    for key in reconcile_status:
        assert (
            reconcile_status[reconcile_fun] == 0 or reconcile_status[reconcile_fun] == 1
        )


def parse_receiver_events(path):
    # { controller_hear id -> controller_hear }
    controller_hear_id_map = {}
    # we need this map to later find the previous controller_hear for each crucial controller_hear
    controller_hear_list = []
    lines = open(path).readlines()
    largest_timestamp = len(lines)
    for i in range(len(lines)):
        line = lines[i]
        if SIEVE_BEFORE_HEAR_MARK in line:
            controller_hear = parse_controller_hear(line)
            controller_hear.start_timestamp = i
            # We initially set the controller_hear end time as the largest timestamp
            # so that if we never meet SIEVE_AFTER_HEAR_MARK for this controller_hear,
            # we will not pose any constraint on its end time in range_overlap
            controller_hear.end_timestamp = largest_timestamp
            controller_hear_id_map[controller_hear.id] = controller_hear
        elif SIEVE_AFTER_HEAR_MARK in line:
            controller_hear_id_only = parse_controller_hear_id_only(line)
            controller_hear_id_map[controller_hear_id_only.id].end_timestamp = i
    for i in range(len(lines)):
        line = lines[i]
        if SIEVE_BEFORE_HEAR_MARK in line:
            controller_hear = parse_controller_hear(line)
            controller_hear_list.append(controller_hear_id_map[controller_hear.id])
    return controller_hear_list


def parse_reconciler_events(test_context: TestContext, path):
    controller_write_start_timestamp_map = {}
    controller_nk_write_start_timestamp_map = {}
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
    # ongoing_reconcile = { reconcile_fun -> number of ongoing workers for this controller }
    ongoing_reconciles = {}
    lines = open(path).readlines()
    for i in range(len(lines)):
        line = lines[i]
        if SIEVE_BEFORE_REST_WRITE_MARK in line:
            controller_write_id_only = parse_controller_write_id_only(line)
            controller_write_start_timestamp_map[controller_write_id_only.id] = i
        elif SIEVE_AFTER_REST_WRITE_MARK in line:
            for key in cur_reconcile_is_trivial:
                cur_reconcile_is_trivial[key] = False
            # If we have not met any reconcile yet, skip the controller_write since it is not caused by reconcile
            # though it should not happen at all.
            # TODO: handle the writes that are not in any reconcile
            controller_write = parse_controller_write(line)
            if controller_write.reconcile_fun not in cur_reconcile_per_type:
                if not test_context.controller_config.loosen_reconciler_boundary:
                    continue
            # Do deepcopy here to ensure the later changes to the two sets
            # will not affect this controller_write.
            # cache read during that possible interval
            controller_write.read_keys = copy.deepcopy(read_keys_this_reconcile)
            controller_write.read_types = copy.deepcopy(read_types_this_reconcile)
            controller_write.start_timestamp = controller_write_start_timestamp_map[
                controller_write.id
            ]
            controller_write.end_timestamp = i
            if controller_write.reconcile_fun in cur_reconcile_per_type:
                prev_reconcile = prev_reconcile_per_type[controller_write.reconcile_fun]
                cur_reconcile = cur_reconcile_per_type[controller_write.reconcile_fun]
                earliest_timestamp = -1
                if prev_reconcile is not None:
                    earliest_timestamp = prev_reconcile.end_timestamp
                controller_write.set_range(earliest_timestamp, i)
                controller_write.reconcile_id = cur_reconcile.reconcile_id
            ts_to_event_map[controller_write.start_timestamp] = controller_write
        elif SIEVE_BEFORE_ANNOTATED_API_INVOCATION_MARK in line:
            id_only = parse_controller_non_k8s_write_id_only(line)
            controller_nk_write_start_timestamp_map[id_only.id] = i
        elif SIEVE_AFTER_ANNOTATED_API_INVOCATION_MARK in line:
            for key in cur_reconcile_is_trivial:
                cur_reconcile_is_trivial[key] = False
            controller_nk_write = parse_controller_non_k8s_write(line)
            if controller_nk_write.reconcile_fun not in cur_reconcile_per_type:
                if not test_context.controller_config.loosen_reconciler_boundary:
                    continue
            controller_nk_write.start_timestamp = (
                controller_nk_write_start_timestamp_map[controller_nk_write.id]
            )
            controller_nk_write.end_timestamp = i
            if controller_nk_write.reconcile_fun in cur_reconcile_per_type:
                prev_reconcile = prev_reconcile_per_type[
                    controller_nk_write.reconcile_fun
                ]
                cur_reconcile = cur_reconcile_per_type[
                    controller_nk_write.reconcile_fun
                ]
                earliest_timestamp = -1
                if prev_reconcile is not None:
                    earliest_timestamp = prev_reconcile.end_timestamp
                controller_nk_write.set_range(earliest_timestamp, i)
                controller_nk_write.reconcile_id = cur_reconcile.reconcile_id
            ts_to_event_map[controller_nk_write.start_timestamp] = controller_nk_write
            print("nk write end")
        elif SIEVE_AFTER_CACHE_READ_MARK in line:
            # TODO: handle the reads that are not in any reconcile
            controller_cache_read = parse_controller_cache_read(line)
            if controller_cache_read.reconcile_fun not in cur_reconcile_per_type:
                continue
            controller_cache_read.end_timestamp = i
            cur_reconcile = cur_reconcile_per_type[controller_cache_read.reconcile_fun]
            controller_cache_read.reconcile_id = cur_reconcile.reconcile_id
            ts_to_event_map[controller_cache_read.end_timestamp] = controller_cache_read
            if controller_cache_read.etype == "Get":
                read_keys_this_reconcile.update(controller_cache_read.key_set)
            else:
                read_types_this_reconcile.add(controller_cache_read.rtype)
        elif SIEVE_BEFORE_RECONCILE_MARK in line:
            reconcile_begin = parse_reconcile(line)
            reconcile_begin.end_timestamp = i
            ts_to_event_map[reconcile_begin.end_timestamp] = reconcile_begin
            reconcile_fun = reconcile_begin.reconcile_fun
            if reconcile_fun not in ongoing_reconciles:
                ongoing_reconciles[reconcile_fun] = 1
            else:
                ongoing_reconciles[reconcile_fun] += 1
            # let's assume there should be only one worker for each controller here
            assert ongoing_reconciles[reconcile_fun] == 1
            if reconcile_fun not in cur_reconcile_per_type:
                prev_reconcile_per_type[reconcile_fun] = None
                cur_reconcile_per_type[reconcile_fun] = reconcile_begin
            else:
                if not test_context.common_config.compress_trivial_reconcile_enabled:
                    prev_reconcile_per_type[reconcile_fun] = cur_reconcile_per_type[
                        reconcile_fun
                    ]
                    cur_reconcile_per_type[reconcile_fun] = reconcile_begin
                elif (
                    test_context.common_config.compress_trivial_reconcile_enabled
                    and not cur_reconcile_is_trivial[reconcile_fun]
                ):
                    prev_reconcile_per_type[reconcile_fun] = cur_reconcile_per_type[
                        reconcile_fun
                    ]
                    cur_reconcile_per_type[reconcile_fun] = reconcile_begin
            cur_reconcile_is_trivial[reconcile_fun] = True
        elif SIEVE_AFTER_RECONCILE_MARK in line:
            reconcile_end = parse_reconcile(line)
            reconcile_end.end_timestamp = i
            ts_to_event_map[reconcile_end.end_timestamp] = reconcile_end
            reconcile_fun = reconcile_end.reconcile_fun
            ongoing_reconciles[reconcile_fun] -= 1
            if ongoing_reconciles[reconcile_fun] == 0:
                del ongoing_reconciles[reconcile_fun]
            # Clear the read keys and types set since all the ongoing reconciles are done
            if len(ongoing_reconciles) == 0:
                read_keys_this_reconcile = set()
                read_types_this_reconcile = set()
    reconciler_event_list = [event for ts, event in sorted(ts_to_event_map.items())]
    return reconciler_event_list


def base_pass(
    controller_hear_vertices: List[EventVertex],
    controller_write_vertices: List[EventVertex],
    controller_non_k8s_write_vertices: List[EventVertex],
):
    print("Running base pass...")
    vertex_pairs = []
    write_vertices = controller_write_vertices + controller_non_k8s_write_vertices
    for controller_write_vertex in write_vertices:
        for controller_hear_vertex in controller_hear_vertices:
            if controller_write_vertex.content.reconcile_id == -1:
                continue
            # controller_hears can lead to that controller_write
            hear_within_reconcile_scope = (
                controller_write_vertex.content.range_start_timestamp
                < controller_hear_vertex.content.end_timestamp
            )
            write_after_hear = (
                controller_write_vertex.content.start_timestamp
                > controller_hear_vertex.content.start_timestamp
            )
            if hear_within_reconcile_scope and write_after_hear:
                vertex_pairs.append([controller_hear_vertex, controller_write_vertex])
    return vertex_pairs


def hear_read_overlap_filtering_pass(vertex_pairs: List[List[EventVertex]]):
    print("Running optional pass: hear-read-overlap-filtering...")
    pruned_vertex_pairs = []
    for pair in vertex_pairs:
        controller_hear_vertex = pair[0]
        controller_write_vertex = pair[1]
        if controller_write_vertex.is_controller_write():
            key_match = (
                controller_hear_vertex.content.key
                in controller_write_vertex.content.read_keys
            )
            type_match = (
                controller_hear_vertex.content.rtype
                in controller_write_vertex.content.read_types
            )
            if key_match or type_match:
                pruned_vertex_pairs.append(pair)
        else:
            pruned_vertex_pairs.append(pair)
    print("<e, s> pairs: {} -> {}".format(len(vertex_pairs), len(pruned_vertex_pairs)))
    return pruned_vertex_pairs


def error_msg_filtering_pass(vertex_pairs: List[List[EventVertex]]):
    print("Running optional pass: error-message-filtering...")
    pruned_vertex_pairs = []
    for pair in vertex_pairs:
        controller_write_vertex = pair[1]
        if controller_write_vertex.is_controller_write():
            if controller_write_vertex.content.error in ALLOWED_ERROR_TYPE:
                pruned_vertex_pairs.append(pair)
        else:
            pruned_vertex_pairs.append(pair)
    print("<e, s> pairs: {} -> {}".format(len(vertex_pairs), len(pruned_vertex_pairs)))
    return pruned_vertex_pairs


def generate_hear_write_pairs(event_graph: EventGraph):
    controller_hear_vertices = event_graph.controller_hear_vertices
    controller_write_vertices = event_graph.controller_write_vertices
    controller_non_k8s_write_vertices = event_graph.controller_non_k8s_write_vertices
    vertex_pairs = base_pass(
        controller_hear_vertices,
        controller_write_vertices,
        controller_non_k8s_write_vertices,
    )
    if HEAR_READ_FILTER_FLAG:
        vertex_pairs = hear_read_overlap_filtering_pass(vertex_pairs)
    return vertex_pairs


def generate_write_hear_pairs(event_graph: EventGraph):
    vertex_pairs = []
    controller_hear_vertices = event_graph.controller_hear_vertices
    controller_write_vertices = event_graph.controller_write_vertices
    controller_hear_key_map = event_graph.controller_hear_key_to_vertices
    for controller_write_vertex in controller_write_vertices:
        if controller_write_vertex.content.key in controller_hear_key_map:
            for controller_hear_vertex in controller_hear_vertices:
                if (
                    controller_hear_vertex.content.obj_str
                    == controller_write_vertex.content.obj_str
                    and controller_write_vertex.content.start_timestamp
                    < controller_hear_vertex.content.start_timestamp
                    and consistent_event_type(
                        controller_hear_vertex.content.etype,
                        controller_write_vertex.content.etype,
                    )
                ):
                    vertex_pairs.append(
                        [controller_write_vertex, controller_hear_vertex]
                    )
                    break
    return vertex_pairs


def build_event_graph(test_context: TestContext, log_path, oracle_dir):
    learned_masked_paths = json.load(open(os.path.join(oracle_dir, "mask.json")))

    controller_hear_list = parse_receiver_events(log_path)
    reconciler_event_list = parse_reconciler_events(test_context, log_path)

    event_graph = EventGraph(
        learned_masked_paths,
        test_context.common_config.field_key_mask,
        test_context.common_config.field_path_mask,
    )
    event_graph.add_sorted_controller_hears(controller_hear_list)
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
    rmtree_if_exists(generated_config_dir)
    os.makedirs(generated_config_dir)
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
    print("Sanity checking the sieve log {}...".format(log_path))
    sanity_check_sieve_log(log_path)

    if not os.path.exists(os.path.join(oracle_dir, "mask.json")):
        fail("cannot find mask.json")
        return
    event_graph = build_event_graph(test_context, log_path, oracle_dir)
    sieve_learn_result = {
        "controller": test_context.controller,
        "test": test_context.test_workload,
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

    result_filename = "{}/{}-{}.json".format(
        test_context.result_root_dir,
        test_context.controller,
        test_context.test_workload,
    )
    with open(result_filename, "w") as test_result_json:
        json.dump(
            sieve_learn_result,
            test_result_json,
            indent=4,
        )
