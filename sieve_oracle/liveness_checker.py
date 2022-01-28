from sieve_common.common import *
import json
import kubernetes
from sieve_oracle.checker_common import *
from sieve_common.default_config import sieve_config
import deepdiff
from deepdiff import DeepDiff
import controllers


def get_resource_helper(func):
    k8s_namespace = sieve_config["namespace"]
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


def get_state_mask(test_context: TestContext):
    return (
        controllers.state_mask[test_context.project]
        if test_context.project in controllers.state_mask
        else {}
    )


def generate_state(test_context: TestContext):
    # print("Generating cluster resources digest...")
    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    apps_v1 = kubernetes.client.AppsV1Api()
    # TODO: we should cover all resource types
    k8s_resource_handler = {
        "deployment": apps_v1.list_namespaced_deployment,
        # "serviceaccount": core_v1.list_namespaced_service_account,
        # "configmap": core_v1.list_namespaced_config_map,
        "secret": core_v1.list_namespaced_secret,
        "persistentvolumeclaim": core_v1.list_namespaced_persistent_volume_claim,
        "pod": core_v1.list_namespaced_pod,
        "service": core_v1.list_namespaced_service,
        "statefulset": apps_v1.list_namespaced_stateful_set,
        "replicaset": apps_v1.list_namespaced_replica_set,
    }

    state = {}
    for rtype in sieve_config["k8s_type_check_list"]:
        state[rtype] = get_resource_helper(k8s_resource_handler[rtype])
    for crd in get_crd_list():
        state[crd] = get_crd(crd)
    return state


def resource_state_masked(
    name,
    namespace,
    resource_type,
    field_key,
    state_mask,
    final_testing_state,
):
    resource_key = "/".join([resource_type, namespace, name])
    if name == "sieve-testing-global-config":
        return True
    elif resource_key in state_mask and field_key in state_mask[resource_key]:
        return True
    tainted_queue = []
    for pod in final_testing_state["pod"]:
        if "sievetag" in final_testing_state["pod"][pod]["metadata"]["labels"]:
            tainted_queue.append(
                ("pod", final_testing_state["pod"][pod]["metadata"]["name"])
            )
    while len(tainted_queue) != 0:
        # print(tainted_queue)
        cur_id = tainted_queue.pop(0)
        cur_type = cur_id[0]
        cur_name = cur_id[1]
        if cur_type == resource_type and cur_name == name:
            return True
        cur_resource = final_testing_state[cur_type][cur_name]
        if "ownerReferences" in cur_resource["metadata"]:
            for owner_ref in cur_resource["metadata"]["ownerReferences"]:
                owner_type = owner_ref["kind"].lower()
                owner_name = owner_ref["name"]
                tainted_queue.append((owner_type, owner_name))
    return False


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


def generate_state_mask_helper(mask_list, predefine, key, obj, path):
    if path in predefine["path"] or key in predefine["key"]:
        mask_list.add(path)
        return
    if type(obj) is str:
        # Check for SIEVE-IGNORE
        if obj == SIEVE_LEARN_VALUE_MASK:
            mask_list.add(path)
            return
        # Check for ignore regex rule
        if match_mask_regex(obj):
            mask_list.add(path)
            return
    if type(obj) is list:
        for i in range(len(obj)):
            val = obj[i]
            newpath = os.path.join(path, "*")
            generate_state_mask_helper(mask_list, predefine, i, val, newpath)
    elif type(obj) is dict:
        for key in obj:
            val = obj[key]
            newpath = os.path.join(path, key)
            generate_state_mask_helper(mask_list, predefine, key, val, newpath)


def generate_state_mask(data):
    mask_map = {}
    for rtype in data:
        mask_map[rtype] = {}
        for name in data[rtype]:
            predefine = {
                "path": set(gen_mask_paths()),
                "key": set(gen_mask_keys()),
            }
            mask_list = set()
            if data[rtype][name] != SIEVE_LEARN_VALUE_MASK:
                generate_state_mask_helper(
                    mask_list, predefine, "", data[rtype][name], ""
                )
                mask_map[rtype][name] = sorted(list(mask_list))
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


# TODO: preprocess is only for backward compability;
# should get rid of it later
def preprocess(learn, test):
    for resource in list(learn):
        if resource not in test:
            learn.pop(resource, None)
    for resource in list(test):
        if resource not in learn:
            test.pop(resource, None)


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


def compare_states(test_context: TestContext):
    canonicalized_state = get_canonicalized_state(test_context)
    testing_state = get_testing_state(test_context)
    state_mask = get_state_mask(test_context)
    final_testing_state = copy.deepcopy(testing_state)

    ret_val = 0
    messages = []
    resource_existence_messages = []
    fields_diff_messages = []
    fields_existence_messages = []

    def nested_get(dic, keys):
        for key in keys:
            dic = dic[key]
        return dic

    preprocess(canonicalized_state, testing_state)
    tdiff = DeepDiff(
        canonicalized_state, testing_state, ignore_order=False, view="tree"
    )
    resource_map = {resource: {"add": [], "remove": []} for resource in testing_state}
    boring_keys = set(gen_mask_keys())
    boring_paths = set(gen_mask_paths())

    for delta_type in tdiff:
        for key in tdiff[delta_type]:
            path = key.path(output_format="list")

            # Handle for resource size diff
            if len(path) == 2:
                resource_type = path[0]
                name = path[1]
                if key.t1 == SIEVE_LEARN_VALUE_MASK:
                    name = SIEVE_LEARN_VALUE_MASK
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

            has_not_care = False
            # Search for boring keys
            for kp in path:
                if kp in boring_keys:
                    has_not_care = True
                    break
            # Search for boring paths
            if len(path) > 2:
                for rule in boring_paths:
                    if equal_path(rule, "/".join([str(x) for x in path[2:]])):
                        has_not_care = True
                        break
            if has_not_care:
                continue

            resource_type = path[0]
            if len(path) == 2 and type(key.t2) is deepdiff.helper.NotPresent:
                source = canonicalized_state
            else:
                source = testing_state

            name = nested_get(source, path[:2] + ["metadata", "name"])
            namespace = nested_get(source, path[:2] + ["metadata", "namespace"])

            resource_key = "/".join([resource_type, namespace, name])
            field_key = ""
            for field in map(str, path[2:]):
                if field.isdigit():
                    field_key += "[%s]" % field
                else:
                    field_key += '["%s"]' % field

            if resource_state_masked(
                name,
                namespace,
                resource_type,
                field_key,
                state_mask,
                final_testing_state,
            ):
                continue

            ret_val += 1
            if delta_type in ["dictionary_item_added", "iterable_item_added"]:
                fields_existence_messages.append(
                    generate_alarm(
                        "End state inconsistency - more object fields than reference:",
                        "{}{} {} {} {}".format(
                            resource_key,
                            field_key,
                            "not seen after reference run, but seen as",
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
                            field_key,
                            "seen as",
                            learned_value,
                            "after reference run, but not seen after testing run",
                        ),
                    )
                )
            elif delta_type == "values_changed":
                fields_diff_messages.append(
                    generate_alarm(
                        "End state inconsistency - object field has a different value:",
                        "{}{} {} {} {} {} {}".format(
                            resource_key,
                            field_key,
                            "is",
                            key.t1,
                            "after reference run, but",
                            key.t2,
                            "after testing run",
                        ),
                    )
                )
            else:
                # TODO: we should fail here
                fields_diff_messages.append(
                    generate_alarm(
                        "End state inconsistency - object field has a different value:",
                        "{} {}{} {} {} {} {}".format(
                            delta_type,
                            resource_key,
                            field_key,
                            "is",
                            key.t1,
                            "after reference run, but",
                            key.t2,
                            "after testing run",
                        ),
                    )
                )

    for resource_type in resource_map:
        resource = resource_map[resource_type]
        # TODO: this is ad-hoc fix
        # the state.json should contain namespace
        # We should revisit this later
        namespace = "default"
        if SIEVE_LEARN_VALUE_MASK in resource["add"] + resource["remove"]:
            # Then we only report number diff
            delta = len(resource["add"]) - len(resource["remove"])
            learn_set = set(canonicalized_state[resource_type].keys())
            test_set = set(testing_state[resource_type].keys())
            if delta != 0:
                ret_val += 1
                resource_existence_messages.append(
                    generate_alarm(
                        "End state inconsistency - more objects than reference:"
                        if delta > 0
                        else "End state inconsistency - fewer objects than reference:",
                        "{} {} {} {} {} {} {} {} {}".format(
                            len(learn_set),
                            resource_type + " object(s)",
                            "seen after reference run",
                            sorted(learn_set),
                            "but",
                            len(test_set),
                            resource_type + " object(s)",
                            "seen after testing run",
                            sorted(test_set),
                        ),
                    )
                )
        else:
            # We report resource diff detail
            for name in resource["add"]:
                # TODO: this is a very ad-hoc fix for dealing with replicaset that hosts controller pod
                # We should revisit it later
                if resource_type == "replicaset" and name.startswith(
                    controllers.deployment_name[test_context.project]
                ):
                    continue
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
            for name in resource["remove"]:
                # TODO: this is a very ad-hoc fix for dealing with replicaset that hosts controller pod
                # We should revisit it later
                if resource_type == "replicaset" and name.startswith(
                    controllers.deployment_name[test_context.project]
                ):
                    continue
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

    resource_existence_messages.sort()
    fields_diff_messages.sort()
    fields_existence_messages.sort()

    messages = (
        resource_existence_messages + fields_diff_messages + fields_existence_messages
    )
    return ret_val, messages
