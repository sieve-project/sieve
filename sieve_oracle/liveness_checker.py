from sieve_common.common import *
import json
import kubernetes
from sieve_oracle.checker_common import *
from sieve_common.default_config import sieve_config
import deepdiff
from deepdiff import DeepDiff


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


def generate_state(test_context: TestContext):
    # print("Generating cluster resources digest...")
    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    apps_v1 = kubernetes.client.AppsV1Api()
    # TODO: should we also cover other types?
    resource_handler = {
        "deployment": apps_v1.list_namespaced_deployment,
        # "serviceaccount": core_v1.list_namespaced_service_account,
        # "configmap": core_v1.list_namespaced_config_map,
        "secret": core_v1.list_namespaced_secret,
        "persistentvolumeclaim": core_v1.list_namespaced_persistent_volume_claim,
        "pod": core_v1.list_namespaced_pod,
        "service": core_v1.list_namespaced_service,
        "statefulset": apps_v1.list_namespaced_stateful_set,
    }
    state = {}

    for resource in resource_handler.keys():
        state[resource] = get_resource_helper(resource_handler[resource])

    crd_list = get_crd_list()
    # Fetch for crd
    for crd in crd_list:
        state[crd] = get_crd(crd)
    return state


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
    can_state = learn_twice_trim(prev_state, cur_state)
    return can_state


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


def preprocess(learn, test):
    for resource in list(learn):
        if resource not in test:
            learn.pop(resource, None)
    for resource in list(test):
        if resource not in learn:
            test.pop(resource, None)


def generic_state_checker(test_context: TestContext):
    learn = json.load(open(os.path.join(test_context.oracle_dir, "state.json")))
    test = json.load(open(os.path.join(test_context.result_dir, "state.json")))

    ret_val = 0
    messages = []

    def nested_get(dic, keys):
        for key in keys:
            dic = dic[key]
        return dic

    preprocess(learn, test)
    tdiff = DeepDiff(learn, test, ignore_order=False, view="tree")
    resource_map = {resource: {"add": [], "remove": []} for resource in test}
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
                source = learn
            else:
                source = test

            name = nested_get(source, path[:2] + ["metadata", "name"])
            namespace = nested_get(source, path[:2] + ["metadata", "namespace"])

            if name == "sieve-testing-global-config":
                continue
            ret_val += 1
            if delta_type in ["dictionary_item_added", "iterable_item_added"]:
                messages.append(
                    generate_alarm(
                        "[RESOURCE-KEY-ADD]",
                        "{} {} {} {} {}".format(
                            "/".join([resource_type, namespace, name]),
                            "/".join(map(str, path[2:])),
                            "not seen during learning run, but seen as",
                            key.t2,
                            "during testing run",
                        ),
                    )
                )
            elif delta_type in ["dictionary_item_removed", "iterable_item_removed"]:
                messages.append(
                    generate_alarm(
                        "[RESOURCE-KEY-REMOVE]",
                        "{} {} {} {} {}".format(
                            "/".join([resource_type, namespace, name]),
                            "/".join(map(str, path[2:])),
                            "seen as",
                            key.t1,
                            "during learning run, but not seen during testing run",
                        ),
                    )
                )
            elif delta_type == "values_changed":
                messages.append(
                    generate_alarm(
                        "[RESOURCE-KEY-DIFF]",
                        "{} {} {} {} {} {} {}".format(
                            "/".join([resource_type, namespace, name]),
                            "/".join(map(str, path[2:])),
                            "is",
                            key.t1,
                            "during learning run, but",
                            key.t2,
                            "during testing run",
                        ),
                    )
                )
            else:
                messages.append(
                    generate_alarm(
                        "[RESOURCE-KEY-UNKNOWN-CHANGE]",
                        "{} {} {} {} {} {} {}".format(
                            delta_type,
                            "/".join([resource_type, namespace, name]),
                            "/".join(map(str, path[2:])),
                            "is",
                            key.t1,
                            " => ",
                            key.t2,
                        ),
                    )
                )

    for resource_type in resource_map:
        resource = resource_map[resource_type]
        if SIEVE_LEARN_VALUE_MASK in resource["add"] + resource["remove"]:
            # Then we only report number diff
            delta = len(resource["add"]) - len(resource["remove"])
            learn_set = set(learn[resource_type].keys())
            test_set = set(test[resource_type].keys())
            if delta != 0:
                ret_val += 1
                messages.append(
                    generate_alarm(
                        "[ALARM][RESOURCE-ADD]"
                        if delta > 0
                        else "[ALARM][RESOURCE-REMOVE]",
                        "{} {} {} {} {} {} {} {} {}".format(
                            len(learn_set),
                            resource_type,
                            "seen after learning run",
                            sorted(learn_set),
                            "but",
                            len(test_set),
                            resource_type,
                            "seen after testing run",
                            sorted(test_set),
                        ),
                    )
                )
        else:
            # We report resource diff detail
            for name in resource["add"]:
                ret_val += 1
                messages.append(
                    generate_alarm(
                        "[ALARM][RESOURCE-ADD]",
                        "{} {}".format(
                            "/".join([resource_type, name]),
                            "is not seen during learning run, but seen during testing run",
                        ),
                    )
                )
            for name in resource["remove"]:
                ret_val += 1
                messages.append(
                    generate_alarm(
                        "[ALARM][RESOURCE-REMOVE]",
                        "{} {}".format(
                            "/".join([resource_type, name]),
                            "is seen during learning run, but not seen during testing run",
                        ),
                    )
                )

    messages.sort()
    return ret_val, messages
