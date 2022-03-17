from sieve_common.common import *
import json
from sieve_oracle.checker_common import *
from sieve_common.k8s_event import get_mask_by_resource_key, parse_key
from deepdiff import DeepDiff


def get_resource_helper(func, namespace):
    k8s_namespace = namespace
    response = func(k8s_namespace, _preload_content=False, watch=False)
    data = json.loads(response.data)
    return {resource["metadata"]["name"]: resource for resource in data["items"]}


def get_crd_list():
    data = []
    try:
        for item in json.loads(os.popen("kubectl get crd -o json").read())["items"]:
            data.append(item["spec"]["names"]["singular"])
    except Exception as e:
        print("get_crd_list fail", e)
    return data


def get_crd(crd):
    data = {}
    try:
        for item in json.loads(os.popen("kubectl get {} -o json".format(crd)).read())[
            "items"
        ]:
            data[item["metadata"]["name"]] = item
    except Exception as e:
        print("get_crd fail", e)
    return data


def generate_state(test_context: TestContext):
    end_state = {}
    deleted = set()
    api_log_path = os.path.join(test_context.result_dir, "apiserver1.log")
    lines = open(api_log_path).readlines()
    lines.reverse()
    for line in lines:
        if SIEVE_API_EVENT_MARK not in line:
            continue
        api_event = parse_api_event(line)
        if api_event.key in deleted or api_event.key in end_state:
            continue
        if api_event.etype == APIEventTypes.DELETED:
            deleted.add(api_event.key)
        else:
            end_state[api_event.key] = api_event.obj_map
    return end_state


def canonicalize_state(test_context: TestContext):
    assert test_context.mode == sieve_modes.LEARN_TWICE
    learn_twice_dir = test_context.result_dir
    cur_state = json.loads(open(os.path.join(learn_twice_dir, "state.json")).read())
    learn_once_dir = os.path.join(
        os.path.dirname(os.path.dirname(test_context.result_dir)),
        "learn-once",
        "learn.yaml",
    )
    prev_state = json.loads(open(os.path.join(learn_once_dir, "state.json")).read())
    canonicalized_state = learn_twice_trim(prev_state, cur_state)
    return canonicalized_state


def generate_state_mask_helper(mask_list, key, obj, path):
    if type(obj) is str:
        if obj == SIEVE_LEARN_VALUE_MASK:
            already_in = False
            for mask in mask_list:
                if mask == path:
                    already_in = True
            if not already_in:
                mask_list.append(path)
            return
    if type(obj) is list:
        for i in range(len(obj)):
            val = obj[i]
            newpath = copy.deepcopy(path)
            newpath.append("*")
            generate_state_mask_helper(mask_list, i, val, newpath)
    elif type(obj) is dict:
        for key in obj:
            val = obj[key]
            newpath = copy.deepcopy(path)
            newpath.append(key)
            generate_state_mask_helper(mask_list, key, val, newpath)


def generate_state_mask(data):
    mask_map = {}
    for key in data:
        mask_list = []
        if data[key] != SIEVE_LEARN_VALUE_MASK:
            generate_state_mask_helper(mask_list, "", data[key], [])
            # make the masked field_path compabitable with controller shape
            metadata_field_set = set(METADATA_FIELDS)
            translated_mask_list = []
            for masked_field_path in mask_list:
                new_masked_field_path = copy.deepcopy(masked_field_path)
                if masked_field_path[0] in metadata_field_set:
                    new_masked_field_path = ["metadata"] + new_masked_field_path
                else:
                    for i in range(len(new_masked_field_path)):
                        new_masked_field_path[i] = (
                            new_masked_field_path[i][:1].lower()
                            + new_masked_field_path[i][1:]
                        )
                translated_mask_list.append(new_masked_field_path)
            translated_mask_list.sort()
            mask_map[key] = translated_mask_list
    return mask_map


def equal_path(template, value):
    template = template.split("/")
    value = value.split("/")

    if len(template) > len(value):
        return False

    for i in range(len(template)):
        if template[i] == "*":
            continue
        if template[i] != value[i]:
            return False
    return True


def get_canonicalized_state(test_context: TestContext):
    canonicalized_state = json.load(
        open(os.path.join(test_context.oracle_dir, "state.json"))
    )
    return canonicalized_state


def get_learning_once_state(test_context: TestContext):
    learn_once_dir = os.path.join(
        os.path.dirname(os.path.dirname(test_context.result_dir)),
        "learn-once",
        "learn.yaml",
    )
    learning_once_state = json.load(open(os.path.join(learn_once_dir, "state.json")))
    return learning_once_state


def get_learning_twice_state(test_context: TestContext):
    learn_twice_dir = os.path.join(
        os.path.dirname(os.path.dirname(test_context.result_dir)),
        "learn-twice",
        "learn.yaml",
    )
    learning_twice_state = json.load(open(os.path.join(learn_twice_dir, "state.json")))
    return learning_twice_state


def get_testing_state(test_context: TestContext):
    testing_state = json.load(open(os.path.join(test_context.result_dir, "state.json")))
    return testing_state


def check_single_state(state, resource_keys, checker_name, customized_checker):
    ret_val = 0
    messages = []
    final_state = {}
    for resource_key in resource_keys:
        tokens = resource_key.split("/")
        rtype = tokens[0]
        ns = tokens[1]
        name = tokens[2]
        final_state[resource_key] = state[rtype][name]
    if not customized_checker(final_state):
        ret_val += 1
        messages.append(
            generate_alarm(
                "[CUSTOMIZED-LIVENESS]",
                "liveness violation: checker {} failed on {}".format(
                    checker_name, final_state
                ),
            )
        )
    return ret_val, messages


def get_objects_from_state_by_type(state, rtype):
    objects = []
    for key in state:
        if key.startswith(rtype + "/"):
            objects.append(key)
    return objects


# TODO: this translation might be too ad-hoc
def tranlate_apiserver_shape_to_controller_shape(path):
    metadata_fields = set(METADATA_FIELDS)
    translated_path = copy.deepcopy(path)
    if len(path) > 1:
        if path[1] in metadata_fields:
            translated_path = translated_path[:1] + ["metadata"] + translated_path[1:]
        else:
            for i in range(1, len(path)):
                if isinstance(translated_path[i], str):
                    if translated_path[i].startswith("SIEVE"):
                        break
                    translated_path[i] = (
                        translated_path[i][:1].lower() + translated_path[i][1:]
                    )
    return translated_path


def resource_key_should_be_masked(
    test_context: TestContext,
    resource_key,
):
    resource_type, namespace, name = parse_key(resource_key)
    if name == "sieve-testing-global-config":
        return True
    else:
        current_controller_family = get_current_controller_related_list(test_context)
        reference_controller_family = get_reference_controller_related_list(
            test_context
        )
        if (
            resource_key in current_controller_family
            or resource_key in reference_controller_family
        ):
            return True
    return False


def resource_field_path_should_be_masked(
    test_context: TestContext, resource_key, field_path_list
):
    # TODO: we should also mask fields as specified in the common_config
    state_mask = test_context.controller_config.end_state_checker_mask
    for test_name in state_mask:
        if test_name == test_context.test_name or test_name == "*":
            if resource_key in state_mask[test_name]:
                for masked_path in state_mask[test_name][resource_key]:
                    field_path_list_prefix = []
                    for field in field_path_list:
                        field_path_list_prefix.append(field)
                        if field_path_list_prefix == masked_path:
                            return True
    return False


def compare_states(test_context: TestContext):
    reference_state = get_canonicalized_state(test_context)
    testing_state = get_testing_state(test_context)

    ret_val = 0
    messages = []
    resource_existence_messages = []
    fields_diff_messages = []
    fields_existence_messages = []

    testing_resource_to_object_map = {}
    reference_resource_to_object_map = {}
    resource_type_with_random_names = set()

    keys_in_testing_state = set(testing_state.keys())
    keys_in_reference_state = set(reference_state.keys())

    for resource_key in keys_in_testing_state.union(keys_in_reference_state):
        if kind_native_objects(resource_key):
            continue
        resource_type, namespace, name = parse_key(resource_key)
        if resource_key in testing_state:
            if resource_type not in testing_resource_to_object_map:
                testing_resource_to_object_map[resource_type] = []
            testing_resource_to_object_map[resource_type].append(resource_key)
        if resource_key in reference_state:
            if resource_type not in reference_resource_to_object_map:
                reference_resource_to_object_map[resource_type] = []
            reference_resource_to_object_map[resource_type].append(resource_key)
            if reference_state[resource_key] == SIEVE_LEARN_VALUE_MASK:
                resource_type_with_random_names.add(resource_type)

    keys_in_testing_state_only = keys_in_testing_state.difference(
        keys_in_reference_state
    )
    keys_in_reference_state_only = keys_in_reference_state.difference(
        keys_in_testing_state
    )

    for resource_key in keys_in_testing_state_only:
        if kind_native_objects(resource_key):
            continue
        if resource_key_should_be_masked(test_context, resource_key):
            continue
        resource_type, namespace, name = parse_key(resource_key)
        if resource_type not in resource_type_with_random_names:
            ret_val += 1
            resource_existence_messages.append(
                generate_alarm(
                    "End state inconsistency - more objects than reference:",
                    "{} {}".format(
                        "/".join([resource_type, namespace, name]),
                        "is not seen after reference run, but seen after testing run",
                    ),
                )
            )
    for resource_key in keys_in_reference_state_only:
        if kind_native_objects(resource_key):
            continue
        if resource_key_should_be_masked(test_context, resource_key):
            continue
        resource_type, namespace, name = parse_key(resource_key)
        if resource_type not in resource_type_with_random_names:
            ret_val += 1
            resource_existence_messages.append(
                generate_alarm(
                    "End state inconsistency - fewer objects than reference:",
                    "{} {}".format(
                        "/".join([resource_type, namespace, name]),
                        "is seen after reference run, but not seen after testing run",
                    ),
                )
            )
    for resource_type in resource_type_with_random_names:
        if resource_type not in testing_resource_to_object_map:
            testing_resource_to_object_map[resource_type] = []
        if resource_type not in reference_resource_to_object_map:
            reference_resource_to_object_map[resource_type] = []
        delta = len(testing_resource_to_object_map[resource_type]) - len(
            reference_resource_to_object_map[resource_type]
        )
        if delta != 0:
            testing_list = testing_resource_to_object_map[resource_type]
            reference_list = reference_resource_to_object_map[resource_type]
            testing_list.sort()
            reference_list.sort()
            ret_val += 1
            resource_existence_messages.append(
                generate_alarm(
                    "End state inconsistency - more objects than reference:"
                    if delta > 0
                    else "End state inconsistency - fewer objects than reference:",
                    "{} {} {} {} {} {} {} {} {}".format(
                        len(reference_list),
                        resource_type + " object(s)",
                        "seen after reference run",
                        reference_list,
                        "but",
                        len(testing_list),
                        resource_type + " object(s)",
                        "seen after testing run",
                        testing_list,
                    ),
                )
            )

    tdiff = DeepDiff(reference_state, testing_state, ignore_order=False, view="tree")
    resource_map = {}

    for delta_type in tdiff:
        for key in tdiff[delta_type]:
            untranslated_path = key.path(output_format="list")
            resource_key = untranslated_path[0]
            if kind_native_objects(resource_key):
                continue
            resource_type, namespace, name = parse_key(resource_key)
            path = untranslated_path
            if (
                resource_type
                not in test_context.controller_config.custom_resource_definitions
            ):
                path = tranlate_apiserver_shape_to_controller_shape(untranslated_path)
            mask_keys = set(
                get_mask_by_resource_key(
                    test_context.common_config.field_key_mask,
                    resource_key,
                )
            )
            mask_paths = set(
                get_mask_by_resource_key(
                    test_context.common_config.field_path_mask,
                    resource_key,
                )
            )

            # Handle for resource size diff
            if len(path) == 1:
                if key.t1 == SIEVE_LEARN_VALUE_MASK:
                    name = SIEVE_LEARN_VALUE_MASK
                resource_map[resource_type] = {"add": [], "remove": []}
                resource_map[resource_type][
                    "add" if delta_type == "dictionary_item_added" else "remove"
                ].append(name)
                continue

            if delta_type in ["values_changed", "type_changes"]:
                if (
                    key.t1 == SIEVE_LEARN_VALUE_MASK
                    or match_mask_regex(key.t1)
                    or match_mask_regex(key.t2)
                ):
                    continue

            should_be_masked = False
            # Search for boring keys
            for kp in path:
                if kp in mask_keys:
                    should_be_masked = True
                    break
            # Search for boring paths
            if len(path) > 2:
                for rule in mask_paths:
                    if equal_path(rule, "/".join([str(x) for x in path[1:]])):
                        should_be_masked = True
                        break
            if should_be_masked:
                continue

            field_path_for_print = ""
            field_path_list = []
            for field in map(str, path[1:]):
                field_path_list.append(str(field))
                if field.isdigit():
                    field_path_for_print += "[%s]" % field
                else:
                    field_path_for_print += '["%s"]' % field

            if resource_key_should_be_masked(
                test_context,
                resource_key,
            ):
                continue

            if resource_field_path_should_be_masked(
                test_context, resource_key, field_path_list
            ):
                continue

            ret_val += 1
            if delta_type in ["dictionary_item_added", "iterable_item_added"]:
                fields_existence_messages.append(
                    generate_alarm(
                        "End state inconsistency - more object fields than reference:",
                        "{}{} {} {} {}".format(
                            resource_key,
                            field_path_for_print,
                            "not seen after reference run, but is",
                            key.t2,
                            "after testing run",
                        ),
                    )
                )
            elif delta_type in ["dictionary_item_removed", "iterable_item_removed"]:
                learned_value = key.t1
                if learned_value == SIEVE_LEARN_VALUE_MASK:
                    learned_value = "a nondeterministic value"
                fields_existence_messages.append(
                    generate_alarm(
                        "End state inconsistency - fewer object fields than reference:",
                        "{}{} {} {} {}".format(
                            resource_key,
                            field_path_for_print,
                            "is",
                            learned_value,
                            "after reference run, but not seen after testing run",
                        ),
                    )
                )
            elif delta_type == "values_changed" or delta_type == "type_changes":
                fields_diff_messages.append(
                    generate_alarm(
                        "End state inconsistency - object field has a different value:",
                        "{}{} {} {} {} {} {}".format(
                            resource_key,
                            field_path_for_print,
                            "is",
                            key.t1,
                            "after reference run, but",
                            key.t2,
                            "after testing run",
                        ),
                    )
                )
            else:
                print(delta_type)
                assert False

    resource_existence_messages.sort()
    fields_diff_messages.sort()
    fields_existence_messages.sort()

    messages = (
        resource_existence_messages + fields_diff_messages + fields_existence_messages
    )
    return ret_val, messages
