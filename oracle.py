import copy
import kubernetes
import analyze_util
import yaml
import json
import os
from common import *
import io
import sieve_config
import re
import deepdiff
from deepdiff import DeepDiff
import pathlib


api_event_empty_entry = {
    analyze_util.APIEventTypes.ADDED: 0,
    analyze_util.APIEventTypes.DELETED: 0,
}


def dump_json_file(dir, data, json_file_name):
    json.dump(
        data, open(os.path.join(dir, json_file_name), "w"), indent=4, sort_keys=True
    )


def generate_test_oracle(project, src_dir, dest_dir, canonicalize_resource=False):
    if sieve_config.config["generate_events_oracle"]:
        events_oracle = generate_events_oracle(project, src_dir, canonicalize_resource)
        dump_json_file(src_dir, events_oracle, "side-effect.json")
        if canonicalize_resource:
            dump_json_file(dest_dir, events_oracle, "side-effect.json")
    if sieve_config.config["generate_status"]:
        status = generate_status()
        dump_json_file(dest_dir, status, "status.json")
    if sieve_config.config["generate_resource"]:
        resources = generate_resources(src_dir, canonicalize_resource)
        # we generate resources.json at src_dir (log dir)
        dump_json_file(src_dir, resources, "resources.json")
        # we generate resoruces.json at dest_dir (data dir) if cononicalize_resource=True
        if canonicalize_resource:
            dump_json_file(dest_dir, resources, "resources.json")


def is_unstable_api_event_key(key, value):
    if value["operator_related"]:
        return True
    if key.endswith("-metrics"):
        return True
    if key.startswith("/endpointslices"):
        return True
    return False


def generate_events_oracle(project, log_dir, canonicalize_resource):
    api_log_path = os.path.join(log_dir, "apiserver1.log")
    api_event_map = {}
    api_key_event_map = {}
    api_type_event_map = {}
    taint_list = []
    for line in open(api_log_path).readlines():
        if analyze_util.SIEVE_API_EVENT_MARK not in line:
            continue
        api_event = analyze_util.parse_api_event(line)
        key = api_event.key
        if (
            api_event.etype != analyze_util.APIEventTypes.ADDED
            and api_event.etype != analyze_util.APIEventTypes.DELETED
        ):
            continue
        if api_event.namespace != "default":
            continue
        generate_name = analyze_util.extract_generate_name(api_event.obj_map)
        if generate_name is not None:
            if analyze_util.is_generated_random_name(api_event.name, generate_name):
                key = key[:-5] + "*"
        assert "/default/" in key
        type_prefix = key[: key.find("/default/")]
        if key not in api_key_event_map:
            api_key_event_map[key] = copy.deepcopy(api_event_empty_entry)
            if analyze_util.operator_related_resource(
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

    if canonicalize_resource:
        # Suppose we are current at learn/learn-twice/xxx
        learn_dir = pathlib.Path(log_dir).parent
        learn_once_dir = learn_dir / "learn-once"
        prev_api_event_map = json.loads(
            open(os.path.join(learn_once_dir, "side-effect.json")).read()
        )
        api_event_map = learn_twice_trim(prev_api_event_map, api_event_map)

        def remove_ignored_value(event_map):
            ignored = set()
            for key in event_map:
                if event_map[key] == "SIEVE-IGNORE":
                    ignored.add(key)
                else:
                    for etype in event_map[key]:
                        if event_map[key][etype] == "SIEVE-IGNORE":
                            ignored.add(key)
                            break
            for key in ignored:
                event_map.pop(key, None)

        remove_ignored_value(api_event_map["keys"])
        remove_ignored_value(api_event_map["types"])

    return api_event_map


def generate_status():
    print("Checking liveness assertions...")
    status = {}
    status_empty_entry = {"size": 0, "terminating": 0}
    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    apps_v1 = kubernetes.client.AppsV1Api()
    k8s_namespace = sieve_config.config["namespace"]
    resources = {}
    for ktype in KTYPES:
        resources[ktype] = []
        if ktype not in status:
            status[ktype] = copy.deepcopy(status_empty_entry)
    for pod in core_v1.list_namespaced_pod(k8s_namespace, watch=False).items:
        if pod.metadata.name in BORING_POD_LIST:
            continue
        resources[POD].append(pod)
    for pvc in core_v1.list_namespaced_persistent_volume_claim(
        k8s_namespace, watch=False
    ).items:
        resources[PVC].append(pvc)
    for dp in apps_v1.list_namespaced_deployment(k8s_namespace, watch=False).items:
        resources[DEPLOYMENT].append(dp)
    for sts in apps_v1.list_namespaced_stateful_set(k8s_namespace, watch=False).items:
        if sts.metadata.name in BORING_STS_LIST:
            continue
        resources[STS].append(sts)
    for ktype in KTYPES:
        status[ktype]["size"] = len(resources[ktype])
        terminating = 0
        for item in resources[ktype]:
            if item.metadata.deletion_timestamp != None:
                terminating += 1
        status[ktype]["terminating"] = terminating
    return status


def get_resource_helper(func):
    k8s_namespace = sieve_config.config["namespace"]
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
        for item in json.loads(os.popen("kubectl get %s -o json" % (crd)).read())[
            "items"
        ]:
            data[item["metadata"]["name"]] = item
    except Exception as e:
        print("get_crd fail", e)
    return data


def learn_twice_trim(base_resources, twice_resources):
    def nested_set(dic, keys, value):
        for key in keys[:-1]:
            dic = dic[key]
        dic[keys[-1]] = value

    stored_learn = copy.deepcopy(base_resources)
    ddiff = DeepDiff(twice_resources, base_resources, ignore_order=False, view="tree")

    if "values_changed" in ddiff:
        for key in ddiff["values_changed"]:
            nested_set(stored_learn, key.path(output_format="list"), "SIEVE-IGNORE")

    if "dictionary_item_added" in ddiff:
        for key in ddiff["dictionary_item_added"]:
            nested_set(stored_learn, key.path(output_format="list"), "SIEVE-IGNORE")

    return stored_learn


def generate_resources(log_dir="", canonicalize_resource=False):
    # print("Generating cluster resources digest...")
    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    apps_v1 = kubernetes.client.AppsV1Api()
    resource_handler = {
        "deployment": apps_v1.list_namespaced_deployment,
        "serviceaccount": core_v1.list_namespaced_service_account,
        "configmap": core_v1.list_namespaced_config_map,
        "secret": core_v1.list_namespaced_secret,
        "persistentvolumeclaim": core_v1.list_namespaced_persistent_volume_claim,
        "pod": core_v1.list_namespaced_pod,
        "service": core_v1.list_namespaced_service,
        "statefulset": apps_v1.list_namespaced_stateful_set,
    }
    resources = {}

    crd_list = get_crd_list()

    resource_set = set(["statefulset", "pod", "persistentvolumeclaim", "deployment"])
    if log_dir != "":
        log_path = os.path.join(log_dir, "sieve-server.log")
        for line in open(log_path).readlines():
            if analyze_util.SIEVE_AFTER_WRITE_MARK not in line:
                continue
            operator_write = analyze_util.parse_operator_write(line)
            resource_set.add(operator_write.rtype)

    for resource in resource_set:
        if resource in resource_handler:
            # Normal resource
            resources[resource] = get_resource_helper(resource_handler[resource])

    # Fetch for crd
    for crd in crd_list:
        resources[crd] = get_crd(crd)

    if canonicalize_resource:
        # Suppose we are current at learn/learn-twice/xxx
        learn_dir = pathlib.Path(log_dir).parent
        learn_once_dir = learn_dir / "learn-once"
        base_resources = json.loads(
            open(os.path.join(learn_once_dir, "resources.json")).read()
        )
        resources = learn_twice_trim(base_resources, resources)
    return resources


def check_status(learning_status, testing_status):
    alarm = 0
    all_keys = set(learning_status.keys()).union(testing_status.keys())
    bug_report = NO_ERROR_MESSAGE
    for rtype in all_keys:
        if rtype not in learning_status:
            bug_report += "[ERROR][STATUS] %s not in learning status digest\n" % (rtype)
            alarm += 1
            continue
        elif rtype not in testing_status:
            bug_report += "[ERROR][STATUS] %s not in testing status digest\n" % (rtype)
            alarm += 1
            continue
        else:
            for attr in learning_status[rtype]:
                if learning_status[rtype][attr] != testing_status[rtype][attr]:
                    alarm += 1
                    bug_report += "[ERROR][STATUS] %s %s inconsistency: %s seen after learning run, but %s seen after testing run\n" % (
                        rtype,
                        attr.upper(),
                        str(learning_status[rtype][attr]),
                        str(testing_status[rtype][attr]),
                    )
    return alarm, bug_report


def check_events_oracle(learning_events, testing_events, test_config, skip_list):
    def should_skip_api_event_key(api_event_key, skip):
        tokens = api_event_key.split("/")
        if tokens[1] == "endpoints":
            rtype = tokens[1]
        elif tokens[1].endswith("s"):
            rtype = tokens[1][:-1]
        else:
            rtype = tokens[1]
        name = tokens[-1]
        for skip_rtype in skip:
            if skip_rtype == rtype:
                for skip_name in skip[skip_rtype]:
                    if skip_name == name and len(skip[skip_rtype][name]) == 0:
                        return True
        return False

    alarm = 0
    bug_report = NO_ERROR_MESSAGE

    test_config_content = yaml.safe_load(open(test_config))
    if test_config_content["mode"] == sieve_modes.OBS_GAP:
        return alarm, bug_report

    # checking events inconsistency for each key
    testing_keys = set(testing_events["keys"].keys())
    learning_keys = set(learning_events["keys"].keys())
    for key in testing_keys.intersection(learning_keys):
        assert learning_events["keys"][key] != "SIEVE-IGNORE"
        if is_unstable_api_event_key(key, learning_events["keys"][key]):
            continue
        if should_skip_api_event_key(key, skip_list):
            continue
        for etype in testing_events["keys"][key]:
            if etype not in sieve_config.config["api_event_to_check"]:
                continue
            assert learning_events["keys"][key][etype] != "SIEVE-IGNORE"
            if (
                testing_events["keys"][key][etype]
                != learning_events["keys"][key][etype]
            ):
                alarm += 1
                bug_report += "[ERROR][EVENT][KEY] %s %s inconsistency: %s events seen during learning run, but %s seen during testing run\n" % (
                    key,
                    etype,
                    str(learning_events["keys"][key][etype]),
                    str(testing_events["keys"][key][etype]),
                )

    if sieve_config.config["check_type_events_oracle"]:
        # checking events inconsistency for each resource type
        testing_rtypes = set(testing_events["types"].keys())
        learning_rtypes = set(learning_events["types"].keys())
        for rtype in testing_rtypes.intersection(learning_rtypes):
            assert learning_events["types"][rtype] != "SIEVE-IGNORE"
            for etype in testing_events["types"][rtype]:
                if etype not in sieve_config.config["api_event_to_check"]:
                    continue
                assert learning_events["types"][rtype][etype] != "SIEVE-IGNORE"
                if (
                    testing_events["types"][rtype][etype]
                    != learning_events["types"][rtype][etype]
                ):
                    alarm += 1
                    bug_report += "[ERROR][EVENT][TYPE] %s %s inconsistency: %s events seen during learning run, but %s seen during testing run\n" % (
                        rtype,
                        etype,
                        str(learning_events["types"][rtype][etype]),
                        str(testing_events["types"][rtype][etype]),
                    )

    return alarm, bug_report


def look_for_panic_in_operator_log(operator_log):
    alarm = 0
    bug_report = NO_ERROR_MESSAGE
    file = open(operator_log)
    for line in file.readlines():
        if "Observed a panic" in line:
            panic_in_file = line[line.find("Observed a panic") :]
            bug_report += "[ERROR][OPERATOR-PANIC] %s" % panic_in_file
            alarm += 1
    return alarm, bug_report


def check_workload_log(workload_log):
    alarm = 0
    bug_report = NO_ERROR_MESSAGE
    file = open(workload_log)
    for line in file.readlines():
        if line.startswith("error:"):
            alarm += 1
            bug_report += "[ERROR][WORKLOAD] %s" % line
    return alarm, bug_report


BORING_EVENT_OBJECT_KEYS = ["image", "imageID"]
# all the path here is full path,
# xxx/0/yyy has the same meaning as xxx/*/yyy
BORING_EVENT_OBJECT_PATHS = [
    "data",
    "metadata/annotations",
    "metadata/managedFields",
    "metadata/labels",
    "metadata/resourceVersion",
    "metadata/generateName",
    "metadata/ownerReferences",
    "metadata/generation",
    "metadata/observedGeneration",
    "spec/containers/0/image",
    "spec/template/spec/containers/0/image",
    "spec/template/spec/containers/0/env",
    "spec/containers/0/env",
    "status/conditions/0/message",
    "spec/containers/0/image",
    "status/containerStatuses/0/image",
    "status/containerStatuses/0/imageID",
    "spec/nodeName",
    "status/conditions/0/type",
    "status/conditions",
    "spec/initContainers/0/image",
]
BORING_IGNORE_MARK = "SIEVE-IGNORE"


def equal_path(template, value):
    template = template.split("/")
    value = value.split("/")

    if len(template) > len(value):
        return False

    for i in range(len(template)):
        if template[i] in ["0", "*"]:
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


def look_for_resources_diff(learn, test):
    f = io.StringIO()
    alarm = 0

    def nested_get(dic, keys):
        for key in keys:
            dic = dic[key]
        return dic

    preprocess(learn, test)
    tdiff = DeepDiff(learn, test, ignore_order=False, view="tree")
    resource_map = {resource: {"add": [], "remove": []} for resource in test}
    not_care_keys = set(BORING_EVENT_OBJECT_KEYS)

    for delta_type in tdiff:
        for key in tdiff[delta_type]:
            path = key.path(output_format="list")

            # Handle for resource size diff
            if len(path) == 2:
                resource_type = path[0]
                name = path[1]
                if key.t1 == BORING_IGNORE_MARK:
                    name = BORING_IGNORE_MARK
                resource_map[resource_type][
                    "add" if delta_type == "dictionary_item_added" else "remove"
                ].append(name)
                continue

            if key.t1 != BORING_IGNORE_MARK:
                has_not_care = False
                # Search for boring keys
                for kp in path:
                    if kp in not_care_keys:
                        has_not_care = True
                        break
                # Search for boring paths
                if len(path) > 2:
                    for rule in BORING_EVENT_OBJECT_PATHS:
                        if equal_path(rule, "/".join([str(x) for x in path[2:]])):
                            has_not_care = True
                            break
                if has_not_care:
                    continue
                # Search for ip
                if type(key.t1) is str:
                    pat = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
                    isip = pat.match(key.t1)
                    if isip:
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
                alarm += 1
                if delta_type in ["dictionary_item_added", "iterable_item_added"]:
                    print(
                        "[ERROR][RESOURCE-KEY-ADD]",
                        "/".join([resource_type, namespace, name]),
                        "/".join(map(str, path[2:])),
                        "not seen during learning run, but seen as",
                        key.t2,
                        "during testing run",
                        file=f,
                    )
                elif delta_type in ["dictionary_item_removed", "iterable_item_removed"]:
                    print(
                        "[ERROR][RESOURCE-KEY-REMOVE]",
                        "/".join([resource_type, namespace, name]),
                        "/".join(map(str, path[2:])),
                        "seen as",
                        key.t1,
                        "during learning run, but not seen",
                        "during testing run",
                        file=f,
                    )
                elif delta_type == "values_changed":
                    print(
                        "[ERROR][RESOURCE-KEY-DIFF]",
                        "/".join([resource_type, namespace, name]),
                        "/".join(map(str, path[2:])),
                        "is",
                        key.t1,
                        "during learning run, but",
                        key.t2,
                        "during testing run",
                        file=f,
                    )
                else:
                    print(
                        delta_type,
                        resource_type,
                        namespace,
                        name,
                        "/".join(map(str, path[2:])),
                        key.t1,
                        " => ",
                        key.t2,
                        file=f,
                    )

    for resource_type in resource_map:
        resource = resource_map[resource_type]
        if BORING_IGNORE_MARK in resource["add"] + resource["remove"]:
            # Then we only report number diff
            delta = len(resource["add"]) - len(resource["remove"])
            learn_set = set(learn[resource_type].keys())
            test_set = set(test[resource_type].keys())
            if delta != 0:
                alarm += 1
                print(
                    "[ERROR][RESOURCE-ADD]"
                    if delta > 0
                    else "[ERROR][RESOURCE-REMOVE]",
                    len(learn_set),
                    resource_type,
                    "seen after learning run",
                    sorted(learn_set),
                    "but",
                    len(test_set),
                    resource_type,
                    "seen after testing run",
                    sorted(test_set),
                    file=f,
                )
        else:
            # We report resource diff detail
            for name in resource["add"]:
                alarm += 1
                print(
                    "[ERROR][RESOURCE-ADD]",
                    "/".join([resource_type, name]),
                    "is not seen during learning run, but seen during testing run",
                    file=f,
                )
            for name in resource["remove"]:
                alarm += 1
                print(
                    "[ERROR][RESOURCE-REMOVE]",
                    "/".join([resource_type, name]),
                    "is seen during learning run, but not seen during testing run",
                    file=f,
                )

    result = f.getvalue()
    f.close()
    final_bug_report = result if alarm != 0 else ""
    return alarm, final_bug_report


def generate_time_travel_debugging_hint(test_config_content):
    desc = "Sieve makes the controller time travel back to the history to see the status just %s %s: %s" % (
        test_config_content["timing"],
        test_config_content["ce-rtype"]
        + "/"
        + test_config_content["ce-namespace"]
        + "/"
        + test_config_content["ce-name"],
        test_config_content["ce-diff-current"],
    )
    suggestion = "Please check how controller reacts when seeing %s: %s, the controller might issue %s to %s without proper checking" % (
        test_config_content["ce-rtype"]
        + "/"
        + test_config_content["ce-namespace"]
        + "/"
        + test_config_content["ce-name"],
        test_config_content["ce-diff-current"],
        "deletion" if test_config_content["se-etype"] == "ADDED" else "creation",
        test_config_content["se-rtype"]
        + "/"
        + test_config_content["se-namespace"]
        + "/"
        + test_config_content["se-name"],
    )
    return desc + "\n" + suggestion + "\n"


def generate_obs_gap_debugging_hint(test_config_content):
    desc = "Sieve makes the controller miss the event %s: %s" % (
        test_config_content["ce-rtype"]
        + "/"
        + test_config_content["ce-namespace"]
        + "/"
        + test_config_content["ce-name"],
        test_config_content["ce-diff-current"],
    )
    suggestion = "Please check how controller reacts when seeing %s: %s, the event can trigger a controller side effect, and it might be cancelled by following events" % (
        test_config_content["ce-rtype"]
        + "/"
        + test_config_content["ce-namespace"]
        + "/"
        + test_config_content["ce-name"],
        test_config_content["ce-diff-current"],
    )
    return desc + "\n" + suggestion + "\n"


def generate_obs_gap_debugging_hint(test_config_content):
    desc = "Sieve makes the controller miss the event %s: %s" % (
        test_config_content["ce-rtype"]
        + "/"
        + test_config_content["ce-namespace"]
        + "/"
        + test_config_content["ce-name"],
        test_config_content["ce-diff-current"],
    )
    suggestion = "Please check how controller reacts when seeing %s: %s, the event can trigger a controller side effect, and it might be cancelled by following events" % (
        test_config_content["ce-rtype"]
        + "/"
        + test_config_content["ce-namespace"]
        + "/"
        + test_config_content["ce-name"],
        test_config_content["ce-diff-current"],
    )
    return desc + "\n" + suggestion + "\n"


def generate_atom_vio_debugging_hint(test_config_content):
    desc = "Sieve makes the controller crash after issuing %s %s: %s" % (
        test_config_content["se-etype-current"],
        test_config_content["se-rtype"]
        + "/"
        + test_config_content["se-namespace"]
        + "/"
        + test_config_content["se-name"],
        test_config_content["se-diff-current"],
    )
    suggestion = "Please check how controller reacts after issuing %s %s: %s, the controller might fail to recover from the dirty state" % (
        test_config_content["se-etype-current"],
        test_config_content["se-rtype"]
        + "/"
        + test_config_content["se-namespace"]
        + "/"
        + test_config_content["se-name"],
        test_config_content["se-diff-current"],
    )
    return desc + "\n" + suggestion + "\n"


def generate_debugging_hint(test_config_content):
    mode = test_config_content["mode"]
    if mode == sieve_modes.TIME_TRAVEL:
        return generate_time_travel_debugging_hint(test_config_content)
    elif mode == sieve_modes.OBS_GAP:
        return generate_obs_gap_debugging_hint(test_config_content)
    elif mode == sieve_modes.ATOM_VIO:
        return generate_atom_vio_debugging_hint(test_config_content)
    else:
        print("mode wrong", mode, test_config_content)
        return "WRONG MODE"


def print_error_and_debugging_info(alarm, bug_report, test_config):
    assert alarm != 0
    test_config_content = yaml.safe_load(open(test_config))
    report_color = bcolors.FAIL if alarm > 0 else bcolors.WARNING
    cprint("[ALARM] %d\n" % (alarm) + bug_report, report_color)
    if sieve_config.config["generate_injection_desc"]:
        hint = "[DEBUGGING SUGGESTION]\n" + generate_debugging_hint(test_config_content)
        cprint(hint, bcolors.WARNING)


def is_time_travel_started(server_log):
    with open(server_log) as f:
        return "START-SIEVE-TIME-TRAVEL" in f.read()


def is_obs_gap_started(server_log):
    with open(server_log) as f:
        return "START-SIEVE-OBSERVABILITY-GAPS" in f.read()


def is_atom_vio_started(server_log):
    with open(server_log) as f:
        return "START-SIEVE-ATOMICITY-VIOLATION" in f.read()


def is_time_travel_finished(server_log):
    with open(server_log) as f:
        return "FINISH-SIEVE-TIME-TRAVEL" in f.read()


def is_obs_gap_finished(server_log):
    with open(server_log) as f:
        return "FINISH-SIEVE-OBSERVABILITY-GAPS" in f.read()


def is_atom_vio_finished(server_log):
    with open(server_log) as f:
        return "FINISH-SIEVE-ATOMICITY-VIOLATION" in f.read()


def is_test_workload_finished(workload_log):
    with open(workload_log) as f:
        return "FINISH-SIEVE-TEST" in f.read()


def injection_validation(test_config, server_log, workload_log):
    test_config_content = yaml.safe_load(open(test_config))
    test_mode = test_config_content["mode"]
    validation_alarm = 0
    validation_report = NO_ERROR_MESSAGE
    if test_mode == sieve_modes.TIME_TRAVEL:
        if not is_time_travel_started(server_log):
            validation_report += "[WARN] time travel is not started yet\n"
            validation_alarm = -1
        elif not is_time_travel_finished(server_log):
            validation_report += "[WARN] time travel is not finished yet\n"
            validation_alarm = -2
    elif test_mode == sieve_modes.OBS_GAP:
        if not is_obs_gap_started(server_log):
            validation_report += "[WARN] obs gap is not started yet\n"
            validation_alarm = -1
        elif not is_obs_gap_finished(server_log):
            validation_report += "[WARN] obs gap is not finished yet\n"
            validation_alarm = -2
    elif test_mode == sieve_modes.ATOM_VIO:
        if not is_atom_vio_started(server_log):
            validation_report += "[WARN] atom vio is not started yet\n"
            validation_alarm = -1
        elif not is_atom_vio_finished(server_log):
            validation_report += "[WARN] atom vio is not finished yet\n"
            validation_alarm = -2
    if not is_test_workload_finished(workload_log):
        validation_report += "[WARN] test workload is not finished yet\n"
        validation_alarm = -2
    return validation_alarm, validation_report


def check(test_config, log_dir, data_dir, skip_list):
    server_log = os.path.join(log_dir, "sieve-server.log")
    workload_log = os.path.join(log_dir, "workload.log")
    validation_alarm, validation_report = injection_validation(
        test_config, server_log, workload_log
    )
    bug_alarm = 0
    bug_report = NO_ERROR_MESSAGE
    if sieve_config.config["check_status"]:
        learn_status = json.load(open(os.path.join(data_dir, "status.json")))
        test_status = json.load(open(os.path.join(log_dir, "status.json")))
        status_alarm, status_bug_report = check_status(learn_status, test_status)
        bug_alarm += status_alarm
        bug_report += status_bug_report

    if sieve_config.config["check_events_oracle"]:
        learn_events = json.load(open(os.path.join(data_dir, "side-effect.json")))
        test_events = json.load(open(os.path.join(log_dir, "side-effect.json")))
        write_alarm, write_bug_report = check_events_oracle(
            learn_events, test_events, test_config, skip_list
        )
        bug_alarm += write_alarm
        bug_report += write_bug_report

    if sieve_config.config["check_operator_log"]:
        operator_log = os.path.join(log_dir, "streamed-operator.log")
        panic_alarm, panic_bug_report = look_for_panic_in_operator_log(operator_log)
        bug_alarm += panic_alarm
        bug_report += panic_bug_report

    if sieve_config.config["check_workload_log"]:
        workload_log = os.path.join(log_dir, "workload.log")
        workload_alarm, workload_bug_report = check_workload_log(workload_log)
        bug_alarm += workload_alarm
        bug_report += workload_bug_report

    if sieve_config.config["check_resource"]:
        learn_resources = json.load(open(os.path.join(data_dir, "resources.json")))
        test_resources = json.load(open(os.path.join(log_dir, "resources.json")))
        resource_alarm, resource_bug_report = look_for_resources_diff(
            learn_resources, test_resources
        )
        bug_alarm += resource_alarm
        bug_report += resource_bug_report

    if validation_alarm < 0:
        return validation_alarm, validation_report + bug_report
    else:
        return bug_alarm, bug_report
