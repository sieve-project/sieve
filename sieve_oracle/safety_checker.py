from sieve_common.common import *
import json
from pathlib import PurePath
from sieve_oracle.checker_common import *
from sieve_common.k8s_event import (
    APIEventTypes,
    SIEVE_API_EVENT_MARK,
    parse_api_event,
    extract_generate_name,
    is_generated_random_name,
)


def masked_resource_key_for_state_update_summary_checker(
    resource_key, test_context: TestContext
):
    test_workload = test_context.test_workload
    controller_mask = test_context.controller_config.state_update_summary_checker_mask
    common_mask = test_context.common_config.state_update_summary_checker_mask
    for masked_test_workload in controller_mask:
        if masked_test_workload == "*" or masked_test_workload == test_workload:
            for masked_key in controller_mask[masked_test_workload]:
                if masked_key == resource_key or PurePath("/" + resource_key).match(
                    "/" + masked_key
                ):
                    print("Skipping %s for state-update-summary checker" % resource_key)
                    return True
    for masked_key in common_mask:
        if masked_key == resource_key or PurePath("/" + resource_key).match(
            "/" + masked_key
        ):
            print("Skipping %s for state-update-summary checker" % resource_key)
            return True
    return False


api_event_empty_entry = {
    APIEventTypes.ADDED: 0,
    APIEventTypes.DELETED: 0,
}


def generate_history(test_context: TestContext):
    api_log_path = os.path.join(test_context.result_dir, "apiserver1.log")
    history = []
    for line in open(api_log_path).readlines():
        if SIEVE_API_EVENT_MARK not in line:
            continue
        api_event = parse_api_event(line)
        api_event_dict = {}
        api_event_dict["number"] = len(history)
        api_event_dict["etype"] = api_event.etype
        api_event_dict["key"] = api_event.key
        api_event_dict["state"] = api_event.obj_str
        history.append(api_event_dict)
    return history


def generate_history_digest(test_context: TestContext):
    log_dir = test_context.result_dir
    api_log_path = os.path.join(log_dir, "apiserver1.log")
    state_update_summary = {}
    for line in open(api_log_path).readlines():
        if SIEVE_API_EVENT_MARK not in line:
            continue
        api_event = parse_api_event(line)
        key = api_event.key
        if (
            api_event.etype
            not in test_context.common_config.state_update_summary_check_event_list
        ):
            continue
        generate_name = extract_generate_name(api_event.obj_map)
        if generate_name is not None:
            if is_generated_random_name(api_event.name, generate_name):
                key = key[:-5] + "*"
        if key not in state_update_summary:
            state_update_summary[key] = copy.deepcopy(api_event_empty_entry)
        state_update_summary[key][api_event.etype] += 1
    return state_update_summary


def canonicalize_history_digest(test_context: TestContext):
    assert test_context.mode == sieve_modes.LEARN_TWICE
    learn_twice_dir = test_context.result_dir
    cur_history_digest = json.loads(
        open(os.path.join(learn_twice_dir, "event.json")).read()
    )
    learn_once_dir = os.path.join(
        os.path.dirname(os.path.dirname(test_context.result_dir)),
        "learn-once",
        "learn.yaml",
    )
    prev_history_digest = json.loads(
        open(os.path.join(learn_once_dir, "event.json")).read()
    )
    can_history_digest = learn_twice_trim(prev_history_digest, cur_history_digest)

    def remove_ignored_value(event_map):
        ignored = set()
        for key in event_map:
            if event_map[key] == SIEVE_LEARN_VALUE_MASK:
                ignored.add(key)
            else:
                for etype in event_map[key]:
                    if event_map[key][etype] == SIEVE_LEARN_VALUE_MASK:
                        ignored.add(key)
                        break
        for key in ignored:
            event_map.pop(key, None)

    remove_ignored_value(can_history_digest)
    return can_history_digest


def get_canonicalized_history_digest(test_context: TestContext):
    can_history_digest = json.load(
        open(os.path.join(test_context.oracle_dir, "event.json"))
    )
    return can_history_digest


def get_learning_once_history_digest(test_context: TestContext):
    learn_once_dir = os.path.join(
        os.path.dirname(os.path.dirname(test_context.result_dir)),
        "learn-once",
        "learn.yaml",
    )
    learning_once_history_digest = json.load(
        open(os.path.join(learn_once_dir, "event.json"))
    )
    return learning_once_history_digest


def get_learning_twice_history_digest(test_context: TestContext):
    learn_twice_dir = os.path.join(
        os.path.dirname(os.path.dirname(test_context.result_dir)),
        "learn-twice",
        "learn.yaml",
    )
    learning_twice_history_digest = json.load(
        open(os.path.join(learn_twice_dir, "event.json"))
    )
    return learning_twice_history_digest


def get_testing_history_digest(test_context: TestContext):
    testing_history_digest = json.load(
        open(os.path.join(test_context.result_dir, "event.json"))
    )
    return testing_history_digest


def get_testing_history_digest(test_context: TestContext):
    testing_history_digest = json.load(
        open(os.path.join(test_context.result_dir, "event.json"))
    )
    return testing_history_digest


def get_learning_once_history(test_context: TestContext):
    learn_once_dir = os.path.join(
        os.path.dirname(os.path.dirname(test_context.result_dir)),
        "learn-once",
        "learn.yaml",
    )
    learning_once_history = json.load(
        open(os.path.join(learn_once_dir, "history.json"))
    )
    return learning_once_history


def get_learning_twice_history(test_context: TestContext):
    learn_twice_dir = os.path.join(
        os.path.dirname(os.path.dirname(test_context.result_dir)),
        "learn-twice",
        "learn.yaml",
    )
    learning_twice_history = json.load(
        open(os.path.join(learn_twice_dir, "history.json"))
    )
    return learning_twice_history


def get_testing_history(test_context: TestContext):
    testing_history = json.load(
        open(os.path.join(test_context.result_dir, "history.json"))
    )
    return testing_history


def get_event_mask(test_context: TestContext):
    return test_context.controller_config.state_update_summary_checker_mask


def apply_safety_checker(
    test_context: TestContext, resource_keys, checker_name, customized_checker
):
    ret_val = 0
    messages = []
    current_state = {}
    history = get_testing_history(test_context)
    for key in resource_keys:
        current_state[key] = None
    for event in history:
        resource_key = event["key"]
        if resource_key in resource_keys:
            if event["etype"] == "DELETED":
                current_state[event["key"]] = None
            else:
                current_state[event["key"]] = event["state"]
            existing_resource_cnt = 0
            for key in current_state:
                if current_state[key] is not None:
                    existing_resource_cnt += 1
            if existing_resource_cnt == len(current_state):
                if not customized_checker(current_state):
                    ret_val += 1
                    messages.append(
                        generate_alarm(
                            "Safety violation:",
                            "checker {} failed on state {} in history.json".format(
                                checker_name, event["number"]
                            ),
                        )
                    )
    messages.sort()
    return ret_val, messages


def compare_history_digests(test_context: TestContext):
    canonicalized_events = get_canonicalized_history_digest(test_context)
    testing_events = get_testing_history_digest(test_context)
    controller_family = get_current_controller_related_list(test_context)

    ret_val = 0
    messages = []

    # checking events inconsistency for each key
    testing_keys = set(testing_events.keys())
    learning_keys = set(canonicalized_events.keys())
    for key in testing_keys.intersection(learning_keys):
        if canonicalized_events[key] == SIEVE_LEARN_VALUE_MASK:
            continue
        if key in controller_family:
            continue
        if masked_resource_key_for_state_update_summary_checker(key, test_context):
            continue
        for etype in testing_events[key]:
            if (
                etype
                not in test_context.common_config.state_update_summary_check_event_list
            ):
                continue
            if canonicalized_events[key][etype] == SIEVE_LEARN_VALUE_MASK:
                continue
            if testing_events[key][etype] != canonicalized_events[key][etype]:
                ret_val += 1
                messages.append(
                    generate_alarm(
                        "State-update summaries inconsistency:",
                        "{} {} inconsistency: {} event(s) seen during reference run, but {} seen during testing run".format(
                            key,
                            etype,
                            str(canonicalized_events[key][etype]),
                            str(testing_events[key][etype]),
                        ),
                    )
                )
    messages.sort()
    return ret_val, messages
