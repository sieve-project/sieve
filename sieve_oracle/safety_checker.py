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
    generate_key,
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
        api_event_dict["etype"] = api_event.etype
        api_event_dict["key"] = api_event.key
        api_event_dict["state"] = api_event.obj_str
        history.append(api_event_dict)
    return history


def generate_history_digest(test_context: TestContext):
    project = test_context.project
    log_dir = test_context.result_dir
    api_log_path = os.path.join(log_dir, "apiserver1.log")
    api_event_map = {}
    api_key_event_map = {}
    api_type_event_map = {}
    taint_list = []
    for line in open(api_log_path).readlines():
        if SIEVE_API_EVENT_MARK not in line:
            continue
        api_event = parse_api_event(line)
        key = api_event.key
        if (
            api_event.etype != APIEventTypes.ADDED
            and api_event.etype != APIEventTypes.DELETED
        ):
            continue
        if api_event.namespace != "default":
            continue
        generate_name = extract_generate_name(api_event.obj_map)
        if generate_name is not None:
            if is_generated_random_name(api_event.name, generate_name):
                key = key[:-5] + "*"
        assert "/default/" in key
        type_prefix = key[: key.find("/default/")]
        if key not in api_key_event_map:
            api_key_event_map[key] = copy.deepcopy(api_event_empty_entry)
            if operator_related_resource(
                project, api_event.rtype, api_event.name, api_event.obj_map, taint_list
            ):
                api_key_event_map[key]["operator_related"] = True
                taint_list.append((api_event.rtype, api_event.name))
            else:
                api_key_event_map[key]["operator_related"] = False
        api_key_event_map[key][api_event.etype] += 1
        if not is_unstable_api_event_key(key, api_key_event_map[key]):
            if type_prefix not in api_type_event_map:
                api_type_event_map[type_prefix] = copy.deepcopy(api_event_empty_entry)
            api_type_event_map[type_prefix][api_event.etype] += 1

    api_event_map["keys"] = api_key_event_map
    api_event_map["types"] = api_type_event_map

    return api_event_map


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

    remove_ignored_value(can_history_digest["keys"])
    remove_ignored_value(can_history_digest["types"])

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
        rtype, ns, name = api_key_to_rtype_namespace_name(event["key"])
        resource_key = generate_key(rtype, ns, name)
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
                            "[CUSTOMIZED-SAFETY]",
                            "safety violation {}: checker {} failed on {}".format(
                                ret_val, checker_name, current_state
                            ),
                        )
                    )
    messages.sort()
    return ret_val, messages


def compare_history_digests(test_context: TestContext):
    canonicalized_events = get_canonicalized_history_digest(test_context)
    testing_events = get_testing_history_digest(test_context)
    event_mask = get_event_mask(test_context)

    ret_val = 0
    messages = []

    # checking events inconsistency for each key
    testing_keys = set(testing_events["keys"].keys())
    learning_keys = set(canonicalized_events["keys"].keys())
    for key in testing_keys.intersection(learning_keys):
        assert canonicalized_events["keys"][key] != SIEVE_LEARN_VALUE_MASK
        if is_unstable_api_event_key(key, canonicalized_events["keys"][key]):
            continue
        if should_skip_api_event_key(key, test_context.test_name, event_mask):
            continue
        for etype in testing_events["keys"][key]:
            if etype not in sieve_config["k8s_event_check_list"]:
                continue
            assert canonicalized_events["keys"][key][etype] != SIEVE_LEARN_VALUE_MASK
            if (
                testing_events["keys"][key][etype]
                != canonicalized_events["keys"][key][etype]
            ):
                ret_val += 1
                rtype, namespace, name = api_key_to_rtype_namespace_name(key)
                resource_key = "/".join([rtype, namespace, name])
                messages.append(
                    generate_alarm(
                        "State-update summaries inconsistency:",
                        "{} {} inconsistency: {} event(s) seen during learning run, but {} seen during testing run".format(
                            resource_key,
                            etype,
                            str(canonicalized_events["keys"][key][etype]),
                            str(testing_events["keys"][key][etype]),
                        ),
                    )
                )
    messages.sort()
    return ret_val, messages
