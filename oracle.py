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
import pathlib


operator_write_empty_entry = {
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


def generate_test_oracle(log_dir, canonicalize_resource=False):
    operator_write, status, resources = generate_digest(log_dir, canonicalize_resource)
    dump_json_file(log_dir, operator_write, "side-effect.json")
    dump_json_file(log_dir, status, "status.json")
    dump_json_file(log_dir, resources, "resources.json")


def generate_digest(log_dir, canonicalize_resource=False):
    operator_write = generate_operator_write(log_dir)
    status = generate_status()
    resources = generate_resources(log_dir, canonicalize_resource)
    return operator_write, status, resources


def generate_operator_write(log_dir):
    print("Checking safety assertions...")
    operator_write_map = {}
    log_path = os.path.join(log_dir, "sieve-server.log")
    for line in open(log_path).readlines():
        if analyze_util.SIEVE_AFTER_WRITE_MARK not in line:
            continue
        operator_write = analyze_util.parse_operator_write(line)
        if analyze_util.ERROR_MSG_FILTER_FLAG:
            # TODO: maybe make the ignored errors configurable
            if operator_write.error not in analyze_util.ALLOWED_ERROR_TYPE:
                continue
        rtype = operator_write.rtype
        namespace = operator_write.namespace
        name = operator_write.name
        etype = operator_write.etype
        if rtype not in operator_write_map:
            operator_write_map[rtype] = {}
        if namespace not in operator_write_map[rtype]:
            operator_write_map[rtype][namespace] = {}
        if name not in operator_write_map[rtype][namespace]:
            operator_write_map[rtype][namespace][name] = copy.deepcopy(
                operator_write_empty_entry
            )
        operator_write_map[rtype][namespace][name][etype] += 1
    return operator_write_map


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
    ddiff = DeepDiff(twice_resources, base_resources, ignore_order=False, view="tree")

    for key in ddiff["values_changed"]:
        nested_set(stored_learn, key.path(output_format="list"), "SIEVE-IGNORE")

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


def preprocess_operator_write(operator_write, interest_objects):
    result = {}
    for interest in interest_objects:
        rtype = interest["rtype"]
        namespace = interest["namespace"]
        name = interest["name"]
        rule = re.compile(name, re.IGNORECASE)
        if rtype in operator_write and namespace in operator_write[rtype]:
            resource_map = operator_write[rtype][namespace]
            se_map = copy.deepcopy(operator_write_empty_entry)
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


def check_operator_write(
    learning_operator_write,
    testing_operator_write,
    test_config,
    oracle_config,
    selective=True,
):
    alarm = 0
    bug_report = NO_ERROR_MESSAGE

    test_config_content = yaml.safe_load(open(test_config))
    if test_config_content["mode"] == sieve_modes.OBS_GAP:
        return alarm, bug_report

    # TODO(wenqing): the interest_object thing should be improved
    # for both time-travel and atom-vio, we should check as many resources as possible
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

    # TODO(wenqing): instead of handling regex now, we should handle it during learn stage using `generateName`
    # Preporcess regex
    learning_operator_write = preprocess_operator_write(
        learning_operator_write, interest_objects
    )
    testing_operator_write = preprocess_operator_write(
        testing_operator_write, interest_objects
    )

    for interest in interest_objects:
        rtype = interest["rtype"]
        namespace = interest["namespace"]
        name = interest["name"]
        exist = True
        if (
            rtype not in learning_operator_write
            or namespace not in learning_operator_write[rtype]
            or name not in learning_operator_write[rtype][namespace]
        ):
            bug_report += (
                "[ERROR][WRITE] %s/%s/%s not in learning side effect digest\n"
                % (
                    rtype,
                    namespace,
                    name,
                )
            )
            alarm += 1
            exist = False
        if (
            rtype not in testing_operator_write
            or namespace not in testing_operator_write[rtype]
            or name not in testing_operator_write[rtype][namespace]
        ):
            bug_report += (
                "[ERROR][WRITE] %s/%s/%s not in testing side effect digest\n"
                % (
                    rtype,
                    namespace,
                    name,
                )
            )
            alarm += 1
            exist = False
        if exist:
            learning_entry = learning_operator_write[rtype][namespace][name]
            testing_entry = testing_operator_write[rtype][namespace][name]
            for attr in learning_entry:
                if selective:
                    if attr not in sieve_config.config["effect_to_check"]:
                        continue
                if learning_entry[attr] != testing_entry[attr]:
                    alarm += 1
                    bug_report += "[ERROR][WRITE] %s/%s/%s %s inconsistency: %s events seen during learning run, but %s seen during testing run\n" % (
                        rtype,
                        namespace,
                        name,
                        attr.upper(),
                        str(learning_entry[attr]),
                        str(testing_entry[attr]),
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
        alarm += 1
        bug_report += "[ERROR][WORKLOAD] %s" % line
    return alarm, bug_report


def look_for_resources_diff(learn, test):
    f = io.StringIO()
    alarm = 0

    def nested_get(dic, keys):
        for key in keys:
            dic = dic[key]
        return dic

    tdiff = DeepDiff(learn, test, ignore_order=False, view="tree")
    not_care_keys = set(BORING_EVENT_OBJECT_FIELDS)

    for delta_type in tdiff:
        for key in tdiff[delta_type]:
            path = key.path(output_format="list")
            if key.t1 != "SIEVE-IGNORE":
                has_not_care = False
                for kp in path:
                    if kp in not_care_keys:
                        has_not_care = True
                        break
                if has_not_care:
                    continue
                try:
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
                except Exception as e:
                    print(e, path, key)

    result = f.getvalue()
    f.close()
    final_bug_report = "[ERROR][RESOURCE]\n" + result if alarm != 0 else ""
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
        test_config_content["se-etype"],
        test_config_content["se-rtype"]
        + "/"
        + test_config_content["se-namespace"]
        + "/"
        + test_config_content["se-name"],
        test_config_content["se-diff-current"],
    )
    suggestion = "Please check how controller reacts after issuing %s %s: %s, the controller might fail to recover from the dirty state" % (
        test_config_content["se-etype"],
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
    hint = "[DEBUGGING SUGGESTION]\n" + generate_debugging_hint(test_config_content)
    report_color = bcolors.FAIL if alarm > 0 else bcolors.WARNING
    cprint("[ALARM] %d\n" % (alarm) + bug_report, report_color)
    cprint(hint, bcolors.WARNING)


def is_time_travel_started(server_log):
    file = open(server_log)
    return "START-SIEVE-TIME-TRAVEL" in file.read()


def is_obs_gap_started(server_log):
    file = open(server_log)
    return "START-SIEVE-OBSERVABILITY-GAPS" in file.read()


def is_atom_vio_started(server_log):
    file = open(server_log)
    return "START-SIEVE-ATOMICITY-VIOLATION" in file.read()


def is_time_travel_finished(server_log):
    file = open(server_log)
    return "FINISH-SIEVE-TIME-TRAVEL" in file.read()


def is_obs_gap_finished(server_log):
    file = open(server_log)
    return "FINISH-SIEVE-OBSERVABILITY-GAPS" in file.read()


def is_atom_vio_finished(server_log):
    file = open(server_log)
    return "FINISH-SIEVE-ATOMICITY-VIOLATION" in file.read()


def injection_detection(test_config, server_log):
    test_config_content = yaml.safe_load(open(test_config))
    test_mode = test_config_content["mode"]
    alarm = 0
    bug_report = NO_ERROR_MESSAGE
    if test_mode == sieve_modes.TIME_TRAVEL:
        if not is_time_travel_started(server_log):
            bug_report = "[WARN] time travel is not started yet\n"
            alarm = -1
        elif not is_time_travel_finished(server_log):
            bug_report = "[WARN] time travel is not finished yet\n"
            alarm = -2
    elif test_mode == sieve_modes.OBS_GAP:
        if not is_obs_gap_started(server_log):
            bug_report = "[WARN] obs gap is not started yet\n"
            alarm = -1
        elif not is_obs_gap_finished(server_log):
            bug_report = "[WARN] obs gap is not finished yet\n"
            alarm = -2
    elif test_mode == sieve_modes.ATOM_VIO:
        if not is_atom_vio_started(server_log):
            bug_report = "[WARN] atom vio is not started yet\n"
            alarm = -1
        elif not is_atom_vio_finished(server_log):
            bug_report = "[WARN] atom vio is not finished yet\n"
            alarm = -2
    return alarm, bug_report


def check(
    learned_operator_write,
    learned_status,
    learned_resources,
    testing_operator_write,
    testing_status,
    testing_resources,
    test_config,
    operator_log,
    server_log,
    oracle_config,
    workload_log,
):

    alarm = 0
    bug_report = NO_ERROR_MESSAGE

    alarm, bug_report = injection_detection(test_config, server_log)
    if alarm != 0:
        return alarm, bug_report

    if sieve_config.config["check_status"]:
        status_alarm, status_bug_report = check_status(learned_status, testing_status)
        alarm += status_alarm
        bug_report += status_bug_report

    if sieve_config.config["check_write"]:
        write_alarm, write_bug_report = check_operator_write(
            learned_operator_write,
            testing_operator_write,
            test_config,
            oracle_config,
        )
        alarm += write_alarm
        bug_report += write_bug_report

    if sieve_config.config["check_operator_log"]:
        panic_alarm, panic_bug_report = look_for_panic_in_operator_log(operator_log)
        alarm += panic_alarm
        bug_report += panic_bug_report

    if sieve_config.config["check_workload_log"]:
        workload_alarm, workload_bug_report = check_workload_log(workload_log)
        alarm += workload_alarm
        bug_report += workload_bug_report

    if sieve_config.config["check_resource"] and learned_resources != None:
        resource_alarm, resource_bug_report = look_for_resources_diff(
            learned_resources, testing_resources
        )
        alarm += resource_alarm
        bug_report += resource_bug_report
    return alarm, bug_report
