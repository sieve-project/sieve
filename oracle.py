import copy
import kubernetes
import analyze_util
import yaml
import jsondiff as jd
import json
import os
from common import *
import io
import sieve_config
import re
import deepdiff
from deepdiff import DeepDiff


side_effect_empty_entry = {
    "Create": 0,
    "Update": 0,
    "Delete": 0,
    "Patch": 0,
    "DeleteAllOf": 0,
}


def dump_json_file(dir, data, json_file_name):
    json.dump(
        data, open(os.path.join(dir, json_file_name), "w"), indent=4, sort_keys=True
    )


def generate_test_oracle(log_dir, data_dir, canonicalize_resource=False):
    log_path = os.path.join(log_dir, "sieve-server.log")
    side_effect, status, resources = generate_digest(log_path, data_dir, canonicalize_resource)
    dump_json_file(log_dir, side_effect, "side-effect.json")
    dump_json_file(log_dir, status, "status.json")
    dump_json_file(log_dir, resources, "resources.json")


def generate_digest(path, canonicalize_resource=False):
    side_effect = generate_side_effect(path)
    status = generate_status()
    resources = generate_resources(path, canonicalize_resource)
    return side_effect, status, resources


def generate_side_effect(path):
    print("Checking safety assertions ...")
    side_effect_map = {}

    for line in open(path).readlines():
        if analyze_util.SIEVE_AFTER_SIDE_EFFECT_MARK not in line:
            continue
        side_effect = analyze_util.parse_side_effect(line)
        if analyze_util.ERROR_MSG_FILTER_FLAG:
            # TODO: maybe make the ignored errors configurable
            if side_effect.error not in analyze_util.ALLOWED_ERROR_TYPE:
                continue
        rtype = side_effect.rtype
        namespace = side_effect.namespace
        name = side_effect.name
        etype = side_effect.etype
        if rtype not in side_effect_map:
            side_effect_map[rtype] = {}
        if namespace not in side_effect_map[rtype]:
            side_effect_map[rtype][namespace] = {}
        if name not in side_effect_map[rtype][namespace]:
            side_effect_map[rtype][namespace][name] = copy.deepcopy(
                side_effect_empty_entry
            )
        side_effect_map[rtype][namespace][name][etype] += 1
    return side_effect_map


def generate_status():
    print("Checking liveness assertions ...")
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
        resources[POD].append(pod)
    for pvc in core_v1.list_namespaced_persistent_volume_claim(
        k8s_namespace, watch=False
    ).items:
        resources[PVC].append(pvc)
    for dp in apps_v1.list_namespaced_deployment(k8s_namespace, watch=False).items:
        resources[DEPLOYMENT].append(dp)
    for sts in apps_v1.list_namespaced_stateful_set(k8s_namespace, watch=False).items:
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
    return [resource for resource in data["items"]]


def get_crd_list():
    data = []
    try:
        for item in json.loads(os.popen("kubectl get crd -o json").read())["items"]:
            data.append(item["spec"]["names"]["singular"])
    except Exception as e:
        print("get_crd_list fail", e)
    return data


def get_crd(crd):
    data = []
    try:
        for item in json.loads(os.popen("kubectl get %s -o json" % (crd)).read())[
            "items"
        ]:
            data.append(item)
    except Exception as e:
        print("get_crd fail", e)
    return data


def learn_twice_trim(base_resources, twice_resources):
    def nested_set(dic, keys, value):
        for key in keys[:-1]:
            dic = dic[key]
        dic[keys[-1]] = value


    stored_learn = copy.deepcopy(base_resources)
    ddiff = DeepDiff(twice_resources, base_resources, ignore_order=False, view='tree')

    for key in ddiff['values_changed']:
        nested_set(stored_learn, key.path(output_format='list'), "SIEVE-IGNORE")

    for key in ddiff['dictionary_item_added']:
        nested_set(stored_learn, key.path(output_format='list'), "SIEVE-IGNORE")

    return stored_learn

def generate_resources(path = "", canonicalize_resource=False):
    # print("Generating cluster resources digest ...")
    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    apps_v1 = kubernetes.client.AppsV1Api()
    resource_handler = {
        "deployment": apps_v1.list_namespaced_deployment,
        "serviceaccount": core_v1.list_namespaced_service_account,
        "configmap": core_v1.list_namespaced_config_map,
        "persistentvolumeclaim": core_v1.list_namespaced_persistent_volume_claim,
        "pod": core_v1.list_namespaced_pod,
        "service": core_v1.list_namespaced_service,
        "statefulset": apps_v1.list_namespaced_stateful_set,
    }
    resources = {}

    crd_list = get_crd_list()

    resource_set = set(["statefulset", "pod", "persistentvolumeclaim", "deployment"])
    if path != "":
        for line in open(path).readlines():
            if analyze_util.SIEVE_AFTER_SIDE_EFFECT_MARK not in line:
                continue
            side_effect = analyze_util.parse_side_effect(line)
            resource_set.add(side_effect.rtype)

    for resource in resource_set:
        if resource in resource_handler:
            # Normal resource
            resources[resource] = get_resource_helper(resource_handler[resource])

    # Fetch for crd
    for crd in crd_list:
        resources[crd] = get_crd(crd)

    if canonicalize_resource and data_dir != "":
        base_resources = json.loads(open(os.path.join(data_dir, "resources.json")).read())
        resources = learn_twice_trim(base_resources, resources)
    return resources


def check_status(learning_status, testing_status):
    alarm = 0
    all_keys = set(learning_status.keys()).union(testing_status.keys())
    bug_report = ""
    for rtype in all_keys:
        if rtype not in learning_status:
            bug_report += "[ERROR] %s not in learning status digest\n" % (rtype)
            alarm += 1
            continue
        elif rtype not in testing_status:
            bug_report += "[ERROR] %s not in testing status digest\n" % (rtype)
            alarm += 1
            continue
        else:
            for attr in learning_status[rtype]:
                if learning_status[rtype][attr] != testing_status[rtype][attr]:
                    alarm += 1
                    bug_report += "[ERROR] %s %s inconsistency: %s seen after learning run, but %s seen after testing run\n" % (
                        rtype,
                        attr.upper(),
                        str(learning_status[rtype][attr]),
                        str(testing_status[rtype][attr]),
                    )
    final_bug_report = (
        "Liveness assertion failed:\n" + bug_report if bug_report != "" else ""
    )
    return alarm, final_bug_report


def preprocess_side_effect(side_effect, interest_objects):
    result = {}
    for interest in interest_objects:
        rtype = interest["rtype"]
        namespace = interest["namespace"]
        name = interest["name"]
        rule = re.compile(name, re.IGNORECASE)
        if rtype in side_effect and namespace in side_effect[rtype]:
            resource_map = side_effect[rtype][namespace]
            se_map = copy.deepcopy(side_effect_empty_entry)
            has_match = False
            for rname in resource_map:
                if rule.fullmatch(rname):
                    has_match = True
                    for setype in resource_map[rname]:
                        se_map[setype] += resource_map[rname][setype]
            if has_match:
                if not rtype in result:
                    result[rtype] = {}
                if not namespace in result[rtype]:
                    result[rtype][namespace] = {}
                result[rtype][namespace][name] = se_map
    return result


def check_side_effect(
    learning_side_effect,
    testing_side_effect,
    interest_objects,
    effect_to_check,
    selective=True,
):
    alarm = 0
    bug_report = ""
    # Preporcess regex
    learning_side_effect = preprocess_side_effect(
        learning_side_effect, interest_objects
    )
    testing_side_effect = preprocess_side_effect(testing_side_effect, interest_objects)

    for interest in interest_objects:
        rtype = interest["rtype"]
        namespace = interest["namespace"]
        name = interest["name"]
        exist = True
        if (
            rtype not in learning_side_effect
            or namespace not in learning_side_effect[rtype]
            or name not in learning_side_effect[rtype][namespace]
        ):
            bug_report += "[ERROR] %s/%s/%s not in learning side effect digest\n" % (
                rtype,
                namespace,
                name,
            )
            alarm += 1
            exist = False
        if (
            rtype not in testing_side_effect
            or namespace not in testing_side_effect[rtype]
            or name not in testing_side_effect[rtype][namespace]
        ):
            bug_report += "[ERROR] %s/%s/%s not in testing side effect digest\n" % (
                rtype,
                namespace,
                name,
            )
            alarm += 1
            exist = False
        if exist:
            learning_entry = learning_side_effect[rtype][namespace][name]
            testing_entry = testing_side_effect[rtype][namespace][name]
            for attr in learning_entry:
                if selective:
                    if attr not in effect_to_check:
                        continue
                if learning_entry[attr] != testing_entry[attr]:
                    alarm += 1
                    bug_report += "[ERROR] %s/%s/%s %s inconsistency: %s events seen during learning run, but %s seen during testing run\n" % (
                        rtype,
                        namespace,
                        name,
                        attr.upper(),
                        str(learning_entry[attr]),
                        str(testing_entry[attr]),
                    )
    final_bug_report = (
        "Safety assertion failed:\n" + bug_report if bug_report != "" else ""
    )
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


def look_for_discrepancy_in_digest(
    learning_side_effect,
    learning_status,
    testing_side_effect,
    testing_status,
    config,
    oracle_config,
):
    test_config_content = yaml.safe_load(open(config))
    alarm_status, bug_report_status = check_status(learning_status, testing_status)
    alarm = alarm_status
    bug_report = bug_report_status
    # TODO: implement side effect checking for obs gap
    if test_config_content["mode"] in [sieve_modes.TIME_TRAVEL, sieve_modes.ATOM_VIO]:
        interest_objects = []
        if test_config_content["mode"] == sieve_modes.TIME_TRAVEL:
            interest_objects.append(
                {
                    "rtype": test_config_content["se-rtype"],
                    "namespace": test_config_content["se-namespace"],
                    "name": test_config_content["se-name"],
                }
            )
        if "interest_objects" in oracle_config:
            interest_objects.extend(oracle_config["interest_objects"])

        effect_to_check = sieve_config.config["effect_to_check"]
        if "effect_to_check" in oracle_config:
            effect_to_check.extend(oracle_config["effect_to_check"])

        alarm_side_effect, bug_report_side_effect = check_side_effect(
            learning_side_effect, testing_side_effect, interest_objects, effect_to_check
        )
        alarm += alarm_side_effect
        bug_report += bug_report_side_effect
    return alarm, bug_report


def look_for_panic_in_operator_log(operator_log):
    alarm = 0
    bug_report = ""
    file = open(operator_log)
    for line in file.readlines():
        if "Observed a panic" in line:
            panic_in_file = line[line.find("Observed a panic") :]
            panic_in_file = panic_in_file.strip()
            bug_report += "[ERROR] %s\n" % panic_in_file
            alarm += 1
    final_bug_report = (
        "Checking for any panic in operator log...\n" + bug_report
        if bug_report != ""
        else ""
    )
    return alarm, final_bug_report


def look_for_sleep_over_in_server_log(server_log):
    file = open(server_log)
    return "[sieve] sleep over" in file.read()


def generate_debugging_hint(test_config_content):
    mode = test_config_content["mode"]
    if mode == sieve_modes.TIME_TRAVEL:
        return generate_time_travel_debugging_hint(test_config_content)
    elif mode == sieve_modes.OBS_GAP:
        return generate_obs_gap_debugging_hint(test_config_content)
    elif mode == sieve_modes.ATOM_VIO:
        return "TODO: generate debugging hint for atomic bugs"
    else:
        print("mode wrong", mode, test_config_content)
        return "WRONG MODE"


def print_error_and_debugging_info(bug_report, test_config):
    test_config_content = yaml.safe_load(open(test_config))
    hint = "[DEBUGGING SUGGESTION]\n" + generate_debugging_hint(test_config_content)
    print(
        bcolors.FAIL
        + "[BUG FOUND]\n"
        + bug_report
        + bcolors.WARNING
        + hint
        + bcolors.ENDC
    )


def check(
    learned_side_effect,
    learned_status,
    learned_resources,
    testing_side_effect,
    testing_status,
    testing_resources,
    test_config,
    operator_log,
    server_log,
    oracle_config,
):
    test_config_content = yaml.safe_load(open(test_config))
    # Skip case which target side effect event not appear in operator log under time-travel mode
    if test_config_content[
        "mode"
    ] == sieve_modes.TIME_TRAVEL and not look_for_sleep_over_in_server_log(server_log):
        bug_report = (
            "[WARN] target side effect event did't appear under time-travel workload"
        )
        print(bug_report)
        return 0, bug_report
    discrepancy_alarm, discrepancy_bug_report = look_for_discrepancy_in_digest(
        learned_side_effect,
        learned_status,
        testing_side_effect,
        testing_status,
        test_config,
        oracle_config,
    )
    panic_alarm, panic_bug_report = look_for_panic_in_operator_log(operator_log)
    alarm = discrepancy_alarm + panic_alarm
    bug_report = discrepancy_bug_report + panic_bug_report
    # TODO(urgent): we should use learned_resources to replace learned_status, instead of using both
    # and look_for_resources_diff() should return alarm as well
    if test_config_content["mode"] != "learn" and learned_resources != None:
        resource_alarm, resource_bug_report = look_for_resources_diff(
            learned_resources, testing_resources
        )
        if resource_alarm != 0:
            alarm += resource_alarm
            bug_report += resource_bug_report
    if alarm != 0:
        print_error_and_debugging_info(bug_report, test_config)
    return alarm, bug_report


def look_for_resources_diff(learn, test):
    f = io.StringIO()
    alarm = 0

    def nested_get(dic, keys):
        for key in keys:
            dic = dic[key]
        return dic

    tdiff = DeepDiff(learn, test, ignore_order=False, view='tree')
    stored_test = copy.deepcopy(test)
    not_care_keys = set(['annotations', 'managedFields', 'image', 'imageID', 'nodeName', 'hostIP', 'message', 'labels', 'generateName', 'ownerReferences', 'podIP', 'ip'])

    for t in tdiff:
        for key in tdiff[t]:
            path = key.path(output_format='list')
            if key.t1 != "SIEVE-IGNORE":
                has_not_care = False
                for kp in path:
                    if kp in not_care_keys:
                        has_not_care = True
                        break
                if has_not_care:
                    continue
                try:
                    rType = path[0]
                    if len(path) == 2 and type(key.t2) is deepdiff.helper.NotPresent:
                        source = learn
                    else:
                        source = test
                    name = nested_get(source, path[:2] + ['metadata', 'name'])
                    namespace = nested_get(source, path[:2] + ['metadata', 'namespace'])
                    if name == "sieve-testing-global-config":
                        continue
                    alarm += 1
                    print(t, rType, namespace, name, '/'.join(map(str, path[2:])), key.t1, " => ", key.t2, file=f)
                except Exception as e:
                    print(e)
                    print(path)
                    print(key)
                    print(test)

    result = f.getvalue()
    f.close()
    return alarm, "[RESOURCE DIFF]\n" + result;


if __name__ == "__main__":
    generate_resources()
