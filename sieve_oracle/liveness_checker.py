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


def generate_state(log_dir="", canonicalize_resource=False):
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
    resources = {}

    for resource in resource_handler.keys():
        resources[resource] = get_resource_helper(resource_handler[resource])

    crd_list = get_crd_list()
    # Fetch for crd
    for crd in crd_list:
        resources[crd] = get_crd(crd)

    if canonicalize_resource:
        # Suppose we are current at learn/learn-twice/learn.yaml/xxx
        learn_dir = os.path.dirname(os.path.dirname(log_dir))
        learn_once_dir = os.path.join(learn_dir, "learn-once", "learn.yaml")
        base_resources = json.loads(
            open(os.path.join(learn_once_dir, "state.json")).read()
        )
        resources = learn_twice_trim(base_resources, resources)
    return resources


def dump_ignore_paths(ignore, predefine, key, obj, path):
    if path in predefine["path"] or key in predefine["key"]:
        ignore.add(path)
        return
    if type(obj) is str:
        # Check for SIEVE-IGNORE
        if obj == SIEVE_LEARN_VALUE_MASK:
            ignore.add(path)
            return
        # Check for ignore regex rule
        if match_mask_regex(obj):
            ignore.add(path)
            return
    if type(obj) is list:
        for i in range(len(obj)):
            val = obj[i]
            newpath = os.path.join(path, "*")
            dump_ignore_paths(ignore, predefine, i, val, newpath)
    elif type(obj) is dict:
        for key in obj:
            val = obj[key]
            newpath = os.path.join(path, key)
            dump_ignore_paths(ignore, predefine, key, val, newpath)


def generate_ignore_paths(data):
    result = {}
    for rtype in data:
        result[rtype] = {}
        for name in data[rtype]:
            predefine = {
                "path": set(gen_mask_paths()),
                "key": set(gen_mask_keys()),
            }
            ignore = set()
            if data[rtype][name] != SIEVE_LEARN_VALUE_MASK:
                dump_ignore_paths(ignore, predefine, "", data[rtype][name], "")
                result[rtype][name] = sorted(list(ignore))
    return result
