import copy
import kubernetes
import analyze_util
import yaml
import common


def generate_digest(path):
    side_effect = generate_side_effect(path)
    status = generate_status()
    return side_effect, status


def generate_side_effect(path):
    print("Generating controller side effect digest ...")
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
    print("Generating cluster status digest ...")
    status = {}
    status_empty_entry = {"size": 0, "terminating": 0}
    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    apps_v1 = kubernetes.client.AppsV1Api()
    k8s_namespace = "default"
    resources = {}
    for ktype in common.KTYPES:
        resources[ktype] = []
        if ktype not in status:
            status[ktype] = copy.deepcopy(status_empty_entry)
    for pod in core_v1.list_namespaced_pod(k8s_namespace, watch=False).items:
        resources[common.POD].append(pod)
    for pvc in core_v1.list_namespaced_persistent_volume_claim(k8s_namespace, watch=False).items:
        resources[common.PVC].append(pvc)
    for dp in apps_v1.list_namespaced_deployment(k8s_namespace, watch=False).items:
        resources[common.DEPLOYMENT].append(dp)
    for sts in apps_v1.list_namespaced_stateful_set(k8s_namespace, watch=False).items:
        resources[common.STS].append(sts)
    for ktype in common.KTYPES:
        status[ktype]["size"] = len(resources[ktype])
        terminating = 0
        for item in resources[ktype]:
            if item.metadata.deletion_timestamp != None:
                terminating += 1
        status[ktype]["terminating"] = terminating
    return status


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
    final_bug_report = "Checking for cluster resource states...\n" + \
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
    final_bug_report = "Checking for controller side effects (resource creation/deletion)...\n" + \
        bug_report if bug_report != "" else ""
    return alarm, final_bug_report


def generate_generate_time_travel_description(testing_config):
    return "Sieve makes the controller time travel back to the history to see the status just %s %s: %s (at %s)" % (
        testing_config["timing"],
        testing_config["ce-rtype"] + "/" +
        testing_config["ce-namespace"] + "/" + testing_config["ce-name"],
        testing_config["ce-diff-current"],
        testing_config["straggler"],
        # testing_config["se-rtype"] + "/" +
        # testing_config["se-namespace"] + "/" + testing_config["se-name"],
        # analyze_util.translate_side_effect(testing_config["se-etype"])
    )


def generate_debug_suggestion(testing_config):
    return "Please check how controller reacts when seeing %s: %s, the event might be cancelled by following events" % (
        testing_config["ce-rtype"] + "/" +
        testing_config["ce-namespace"] + "/" + testing_config["ce-name"],
        testing_config["ce-diff-current"])


def look_for_discrepancy_in_digest(learning_side_effect, learning_status, testing_side_effect, testing_status, config):
    testing_config = yaml.safe_load(open(config))
    alarm_status, bug_report_status = check_status(
        learning_status, testing_status)
    alarm = alarm_status
    bug_report = bug_report_status
    # TODO: implement side effect checking for obs gap
    if testing_config["mode"] == "time-travel":
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
    return "[sonar] sleep over" in file.read()


def check(learned_side_effect, learned_status, testing_side_effect, testing_status, test_config, operator_log, server_log):
    testing_config = yaml.safe_load(open(test_config))
    # Skip case which target side effect event not appear in operator log under time-travel mode
    if testing_config["mode"] == "time-travel" and not look_for_sleep_over_in_server_log(server_log):
        bug_report = "[WARN] target side effect event did't appear under time-travel workload"
        print(bug_report)
        return bug_report
    discrepancy_alarm, discrepancy_bug_report = look_for_discrepancy_in_digest(
        learned_side_effect, learned_status, testing_side_effect, testing_status, test_config)
    panic_alarm, panic_bug_report = look_for_panic_in_operator_log(
        operator_log)
    alarm = discrepancy_alarm + panic_alarm
    bug_report = discrepancy_bug_report + panic_bug_report
    if alarm != 0:
        if testing_config["mode"] == "time-travel":
            bug_report += "[TIME TRAVEL DESCRIPTION] %s\n" % generate_generate_time_travel_description(
                testing_config)
            bug_report += "[DEBUGGING SUGGESTION] %s\n" % generate_debug_suggestion(
                testing_config)
        bug_report = "\n[BUG REPORT]\n" + bug_report
        print(bug_report)
    return bug_report
