from sieve_common.common import *
import json
import kubernetes
from sieve_oracle.checker_common import *
from sieve_common.default_config import sieve_config
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
