from sieve_common.common import *
import json
from sieve_oracle.checker_common import *
from sieve_common.k8s_event import (
    APIEventTypes,
    SIEVE_API_EVENT_MARK,
    parse_api_event,
    extract_generate_name,
    is_generated_random_name,
    operator_related_resource,
    api_key_to_rtype_namespace_name,
)
from sieve_common.default_config import sieve_config
import controllers


def is_unstable_api_event_key(key, value):
    if value["operator_related"]:
        return True
    if key.endswith("-metrics"):
        return True
    if key.startswith("/endpointslices"):
        return True
    return False


def should_skip_api_event_key(api_event_key, test_name, masked):
    rtype, _, name = api_key_to_rtype_namespace_name(api_event_key)
    for masked_test_name in masked:
        if masked_test_name == "*" or masked_test_name == test_name:
            for masked_rtype in masked[masked_test_name]:
                if masked_rtype == rtype:
                    if name in masked[masked_test_name][masked_rtype]:
                        return True
    return False


def get_learning_history_digest(test_context: TestContext):
    learning_history_digest = json.load(
        open(os.path.join(test_context.oracle_dir, "event.json"))
    )
    return learning_history_digest


def get_testing_history_digest(test_context: TestContext):
    testing_history_digest = json.load(
        open(os.path.join(test_context.result_dir, "event.json"))
    )
    return testing_history_digest


def get_testing_history(test_context: TestContext):
    testing_history = json.load(
        open(os.path.join(test_context.result_dir, "history.json"))
    )
    return testing_history


def get_event_mask(test_context: TestContext):
    return (
        controllers.event_mask[test_context.project]
        if test_context.project in controllers.event_mask
        else {}
    )


def check_single_history(history, resource_keys, checker_name, customized_checker):
    ret_val = 0
    messages = []
    current_state = {}
    for key in resource_keys:
        current_state[key] = None
    for event in history:
        if event["key"] in resource_keys:
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
                            "[CUSTOMIZED-SAFETY]",
                            "safety violation {}: checker {} failed on {}".format(
                                ret_val, checker_name, current_state
                            ),
                        )
                    )
    messages.sort()
    return ret_val, messages


def compare_history_digests(test_context: TestContext):
    learning_events = get_learning_history_digest(test_context)
    testing_events = get_testing_history_digest(test_context)
    test_name = test_context.test_name
    event_mask = get_event_mask(test_context)

    ret_val = 0
    messages = []

    # checking events inconsistency for each key
    testing_keys = set(testing_events["keys"].keys())
    learning_keys = set(learning_events["keys"].keys())
    for key in testing_keys.intersection(learning_keys):
        assert learning_events["keys"][key] != "SIEVE-IGNORE"
        if is_unstable_api_event_key(key, learning_events["keys"][key]):
            continue
        if should_skip_api_event_key(key, test_name, event_mask):
            continue
        for etype in testing_events["keys"][key]:
            if etype not in sieve_config["api_event_to_check"]:
                continue
            assert learning_events["keys"][key][etype] != "SIEVE-IGNORE"
            if (
                testing_events["keys"][key][etype]
                != learning_events["keys"][key][etype]
            ):
                ret_val += 1
                messages.append(
                    generate_alarm(
                        "[EVENT][KEY]",
                        "{} {} inconsistency: {} events seen during learning run, but {} seen during testing run".format(
                            key,
                            etype,
                            str(learning_events["keys"][key][etype]),
                            str(testing_events["keys"][key][etype]),
                        ),
                    )
                )
    messages.sort()
    return ret_val, messages
