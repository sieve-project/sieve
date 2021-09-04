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

not_care_keys = ['uid', 'resourceVersion', 'creationTimestamp', 'ownerReferences', 'managedFields', 'generateName', 'selfLink', 'annotations',
                 'pod-template-hash', 'secretName', 'image', 'lastTransitionTime', 'nodeName', 'podIPs', 'podIP', 'hostIP', 'containerID', 'imageID',
                 'startTime', 'startedAt', 'volumeMounts', 'finishedAt', 'volumeName', 'lastUpdateTime', 'env', 'message', 'currentRevision', 'updateRevision',
                 'controller-revision-hash']
not_care = [jd.delete, jd.insert] + not_care_keys + ['name']


def generate_digest(path):
    side_effect = generate_side_effect(path)
    status = generate_status()
    resources = generate_resources()
    return side_effect, status, resources


def generate_side_effect(path):
    print("Checking safety assertions ...")
    side_effect_map = {}
    side_effect_empty_entry = {"Create": 0, "Update": 0,
                               "Delete": 0, "Patch": 0, "DeleteAllOf": 0}
    for line in open(path).readlines():
        if analyze_util.SONAR_SIDE_EFFECT_MARK not in line:
            continue
        side_effect = analyze_util.parse_side_effect(line)
        if analyze_util.ERROR_MSG_FILTER_FLAG:
            if side_effect.error == "NotFound":
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
                side_effect_empty_entry)
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
    for pvc in core_v1.list_namespaced_persistent_volume_claim(k8s_namespace, watch=False).items:
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


def trim_resource(cur, key_trace=[]):
    if type(cur) is list:
        idx = 0
        for item in cur:
            trim_resource(item, key_trace)
            idx += 1

    if type(cur) is dict:
        for key in list(cur):
            if key in not_care_keys:
                cur[key] = "SIEVE-IGNORE"
            elif key == 'name' and key_trace[1] != "metadata":
                cur[key] = "SIEVE-IGNORE"
            else:
                trim_resource(cur[key], key_trace + [key])


def get_resource_helper(func):
    k8s_namespace = sieve_config.config["namespace"]
    response = func(k8s_namespace, _preload_content=False, watch=False)
    data = json.loads(response.data)
    return [resource for resource in data['items']]


def get_crd_list():
    data = []
    try:
        for item in json.loads(os.popen('kubectl get crd -o json').read())["items"]:
            data.append(item["spec"]["names"]["singular"])
    except Exception as e:
        print("get_crd_list fail", e)
    return data


def get_crd(crd):
    data = []
    try:
        for item in json.loads(os.popen('kubectl get %s -o json' % (crd)).read())["items"]:
            data.append(item)
    except Exception as e:
        print("get_crd fail", e)
    return data


def generate_resources(path=""):
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
        "statefulset": apps_v1.list_namespaced_stateful_set
    }
    resources = {}

    crd_list = get_crd_list()

    resource_set = set(
        ["statefulset", "pod", "persistentvolumeclaim", "deployment"])
    if path != "":
        for line in open(path).readlines():
            if analyze_util.SONAR_SIDE_EFFECT_MARK not in line:
                continue
            side_effect = analyze_util.parse_side_effect(line)
            resource_set.add(side_effect.rtype)

    for resource in resource_set:
        if resource in resource_handler:
            # Normal resource
            resources[resource] = get_resource_helper(
                resource_handler[resource])

    # Fetch for crd
    for crd in crd_list:
        resources[crd] = get_crd(crd)

    trim_resource(resources)
    return resources


def check_status(learning_status, testing_status):
    alarm = 0
    all_keys = set(learning_status.keys()).union(
        testing_status.keys())
    bug_report = ""
    for rtype in all_keys:
        if rtype not in learning_status:
            bug_report += "[ERROR] %s not in learning status digest\n" % (
                rtype)
            alarm += 1
            continue
        elif rtype not in testing_status:
            bug_report += "[ERROR] %s not in testing status digest\n" % (
                rtype)
            alarm += 1
            continue
        else:
            for attr in learning_status[rtype]:
                if learning_status[rtype][attr] != testing_status[rtype][attr]:
                    alarm += 1
                    bug_report += "[ERROR] %s %s inconsistency: %s seen after learning run, but %s seen after testing run\n" % (
                        rtype, attr.upper(), str(learning_status[rtype][attr]), str(testing_status[rtype][attr]))
    final_bug_report = "Liveness assertion failed:\n" + \
        bug_report if bug_report != "" else ""
    return alarm, final_bug_report


def check_side_effect(learning_side_effect, testing_side_effect, interest_objects, selective=True):
    alarm = 0
    bug_report = ""
    for interest in interest_objects:
        rtype = interest["rtype"]
        namespace = interest["namespace"]
        name = interest["name"]
        exist = True
        if rtype not in learning_side_effect or namespace not in learning_side_effect[rtype] or name not in learning_side_effect[rtype][namespace]:
            bug_report += "[ERROR] %s/%s/%s not in learning side effect digest\n" % (
                rtype, namespace, name)
            alarm += 1
            exist = False
        if rtype not in testing_side_effect or namespace not in testing_side_effect[rtype] or name not in testing_side_effect[rtype][namespace]:
            bug_report += "[ERROR] %s/%s/%s not in testing side effect digest\n" % (
                rtype, namespace, name)
            alarm += 1
            exist = False
        if exist:
            learning_entry = learning_side_effect[rtype][namespace][name]
            testing_entry = testing_side_effect[rtype][namespace][name]
            for attr in learning_entry:
                if selective:
                    if attr == "Update" or attr == "Patch":
                        continue
                if learning_entry[attr] != testing_entry[attr]:
                    alarm += 1
                    bug_report += "[ERROR] %s/%s/%s %s inconsistency: %s events seen during learning run, but %s seen during testing run\n" % (
                        rtype, namespace, name, attr.upper(), str(learning_entry[attr]), str(testing_entry[attr]))
    final_bug_report = "Safety assertion failed:\n" + \
        bug_report if bug_report != "" else ""
    return alarm, final_bug_report


def generate_time_travel_debugging_hint(testing_config):
    desc = "Sieve makes the controller time travel back to the history to see the status just %s %s: %s" % (
        testing_config["timing"],
        testing_config["ce-rtype"] + "/" +
        testing_config["ce-namespace"] + "/" + testing_config["ce-name"],
        testing_config["ce-diff-current"])
    suggestion = "Please check how controller reacts when seeing %s: %s, the controller might issue %s to %s without proper checking" % (
        testing_config["ce-rtype"] + "/" +
        testing_config["ce-namespace"] + "/" + testing_config["ce-name"],
        testing_config["ce-diff-current"],
        "deletion" if testing_config["se-etype"] == "ADDED" else "creation",
        testing_config["se-rtype"] + "/" + testing_config["se-namespace"] + "/" + testing_config["se-name"])
    return desc + "\n" + suggestion + "\n"


def generate_obs_gap_debugging_hint(testing_config):
    desc = "Sieve makes the controller miss the event %s: %s" % (
        testing_config["ce-rtype"] + "/" +
        testing_config["ce-namespace"] + "/" + testing_config["ce-name"],
        testing_config["ce-diff-current"])
    suggestion = "Please check how controller reacts when seeing %s: %s, the event can trigger a controller side effect, and it might be cancelled by following events" % (
        testing_config["ce-rtype"] + "/" +
        testing_config["ce-namespace"] + "/" + testing_config["ce-name"],
        testing_config["ce-diff-current"])
    return desc + "\n" + suggestion + "\n"


def look_for_discrepancy_in_digest(learning_side_effect, learning_status, testing_side_effect, testing_status, config):
    testing_config = yaml.safe_load(open(config))
    alarm_status, bug_report_status = check_status(
        learning_status, testing_status)
    alarm = alarm_status
    bug_report = bug_report_status
    # TODO: implement side effect checking for obs gap
    if testing_config["mode"] == sieve_modes.TIME_TRAVEL:
        interest_objects = []
        interest_objects.append(
            {"rtype": testing_config["se-rtype"], "namespace": testing_config["se-namespace"], "name": testing_config["se-name"]})
        alarm_side_effect, bug_report_side_effect = check_side_effect(
            learning_side_effect, testing_side_effect, interest_objects)
        alarm += alarm_side_effect
        bug_report += bug_report_side_effect
    return alarm, bug_report


def look_for_panic_in_operator_log(operator_log):
    alarm = 0
    bug_report = ""
    file = open(operator_log)
    for line in file.readlines():
        if "Observed a panic" in line:
            panic_in_file = line[line.find("Observed a panic"):]
            panic_in_file = panic_in_file.strip()
            bug_report += "[ERROR] %s\n" % panic_in_file
            alarm += 1
    final_bug_report = "Checking for any panic in operator log...\n" + \
        bug_report if bug_report != "" else ""
    return alarm, final_bug_report


def look_for_sleep_over_in_server_log(server_log):
    file = open(server_log)
    return "[sieve] sleep over" in file.read()


def generate_debugging_hint(testing_config):
    mode = testing_config["mode"]
    if mode == sieve_modes.TIME_TRAVEL:
        return generate_time_travel_debugging_hint(testing_config)
    elif mode == sieve_modes.OBS_GAP:
        return generate_obs_gap_debugging_hint(testing_config)
    elif mode == sieve_modes.ATOM_VIO:
        return "TODO: generate debugging hint for atomic bugs"
    else:
        assert False


def check(learned_side_effect, learned_status, learned_resources, testing_side_effect, testing_status, testing_resources, test_config, operator_log, server_log):
    testing_config = yaml.safe_load(open(test_config))
    # Skip case which target side effect event not appear in operator log under time-travel mode
    if testing_config["mode"] == sieve_modes.TIME_TRAVEL and not look_for_sleep_over_in_server_log(server_log):
        bug_report = "[WARN] target side effect event did't appear under time-travel workload"
        print(bug_report)
        return bug_report
    discrepancy_alarm, discrepancy_bug_report = look_for_discrepancy_in_digest(
        learned_side_effect, learned_status, testing_side_effect, testing_status, test_config)
    panic_alarm, panic_bug_report = look_for_panic_in_operator_log(
        operator_log)
    alarm = discrepancy_alarm + panic_alarm
    bug_report = discrepancy_bug_report + panic_bug_report
    if learned_resources != None:
        bug_report += "\n" + \
            look_for_resouces_diff(learned_resources, testing_resources)
    if alarm != 0:
        bug_report = "[BUG FOUND]\n" + bug_report
        hint = "[DEBUGGING SUGGESTION]\n" + \
            generate_debugging_hint(testing_config)
        print(bcolors.FAIL + bug_report + bcolors.WARNING + hint + bcolors.ENDC)
        bug_report += hint
    return bug_report


def look_for_resouces_diff(learn, test):
    f = io.StringIO()
    learn_trim = copy.deepcopy(learn)
    test_trim = copy.deepcopy(test)
    trim_resource(learn_trim)
    trim_resource(test_trim)
    diff = jd.diff(learn_trim, test_trim, syntax='symmetric')

    print("[RESOURCE DIFF REPORT]", file=f)
    for rtype in diff:
        rdiff = diff[rtype]
        # Check for resource level delete/insert
        if jd.delete in rdiff:
            # Any resource deleted
            for (idx, item) in rdiff[jd.delete]:
                print("[resource deleted]", rtype, item['metadata']
                      ['namespace'], item['metadata']['name'], file=f)
        if jd.insert in rdiff:
            # Any resource added
            for (idx, item) in rdiff[jd.insert]:
                print("[resource added]", rtype, item['metadata']
                      ['namespace'], item['metadata']['name'], file=f)

        # Check for resource internal fields
        for idx in rdiff:
            if not type(idx) is int:
                continue
            resource = test[rtype][idx]
            name = resource['metadata']['name']
            namespace = resource['metadata']['namespace']
            item = rdiff[idx]
            for majorfield in item:
                if majorfield == jd.delete:
                    print("[field deleted]", item[majorfield], file=f)
                    continue
                if majorfield == jd.insert:
                    print("[field added]", item[majorfield], file=f)
                    continue
                data = item[majorfield]
                for subfield in data:
                    if not subfield in not_care:
                        print("[%s field changed]" % (majorfield), rtype, name,
                              subfield, "changed", "delta: ", data[subfield], file=f)
                if jd.delete in data:
                    print("[%s field deleted]" % (majorfield),
                          rtype, name, data[jd.delete], file=f)
                if jd.insert in data:
                    print("[%s field added]" % (majorfield),
                          rtype, name, data[jd.insert], file=f)

    result = f.getvalue()
    f.close()
    return result


if __name__ == "__main__":
    generate_resources()
