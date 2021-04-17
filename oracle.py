import constant
import copy
import kubernetes


def generate_digest(path):
    side_effect = generate_side_effect(path)
    status = generate_status()
    return side_effect, status


def generate_side_effect(path):
    side_effect = {}
    side_effect_empty_entry = {"create": 0, "update": 0,
                               "delete": 0, "patch": 0, "deleteallof": 0}
    for line in open(path).readlines():
        if constant.SONAR_SIDE_EFFECT_MARK not in line:
            continue
        line = line[line.find(constant.SONAR_SIDE_EFFECT_MARK):].strip("\n")
        tokens = line.split("\t")
        effectType = tokens[1].lower()
        rType = tokens[2]
        if constant.ERROR_FILTER:
            if tokens[5] == "NotFound":
                continue
        if rType not in side_effect:
            side_effect[rType] = copy.deepcopy(side_effect_empty_entry)
        side_effect[rType][effectType] += 1
    return side_effect


def generate_status():
    status = {}
    status_empty_entry = {"size": 0, "terminating": 0}
    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    apps_v1 = kubernetes.client.AppsV1Api()
    k8s_namespace = "default"
    resources = {}
    for ktype in constant.KTYPES:
        resources[ktype] = []
        if ktype not in status:
            status[ktype] = copy.deepcopy(status_empty_entry)
    for pod in core_v1.list_namespaced_pod(k8s_namespace, watch=False).items:
        resources[constant.POD].append(pod)
    for pvc in core_v1.list_namespaced_persistent_volume_claim(k8s_namespace, watch=False).items:
        resources[constant.PVC].append(pvc)
    for dp in apps_v1.list_namespaced_deployment(k8s_namespace, watch=False).items:
        resources[constant.DEPLOYMENT].append(dp)
    for sts in apps_v1.list_namespaced_stateful_set(k8s_namespace, watch=False).items:
        resources[constant.STS].append(sts)
    for ktype in constant.KTYPES:
        status[ktype]["size"] = len(resources[ktype])
        terminating = 0
        for item in resources[ktype]:
            if item.metadata.deletion_timestamp != None:
                terminating += 1
        status[ktype]["terminating"] = terminating
    return status


def compare_map(learned_map, testing_map, map_type):
    alarm = 0
    all_keys = set(learned_map.keys()).union(
        testing_map.keys())
    bug_report = "[BUG REPORT] %s\n" % map_type
    for rtype in all_keys:
        if rtype not in learned_map:
            bug_report += "[ERROR] %s not in learning %s digest\n" % (
                rtype, map_type)
            alarm += 1
            continue
        elif rtype not in testing_map:
            bug_report += "[ERROR] %s not in testing %s digest\n" % (
                rtype, map_type)
            alarm += 1
            continue
        else:
            for attr in learned_map[rtype]:
                if attr not in testing_map[rtype]:
                    print("[WARN] attr: %s not int rtype: %s: " %
                          (attr, rtype), testing_map[rtype])
                    continue
                if learned_map[rtype][attr] != testing_map[rtype][attr]:
                    level = "WARN" if attr == "update" else "ERROR"
                    alarm += 0 if attr == "update" else 1
                    bug_report += "[%s] %s.%s inconsistent: learning: %s, testing: %s\n" % (
                        level, rtype, attr, str(learned_map[rtype][attr]), str(testing_map[rtype][attr]))
    return alarm, bug_report


def compare_digest(learned_side_effect, learned_status, testing_side_effect, testing_status):
    alarm_side_effect, bug_report_side_effect = compare_map(
        learned_side_effect, testing_side_effect, "side effect")
    alarm_status, bug_report_status = compare_map(
        learned_status, testing_status, "status")
    alarm = alarm_side_effect + alarm_status
    bug_report = bug_report_side_effect + bug_report_status
    if alarm != 0:
        bug_report += "[BUGGY] # alarms: %d\n" % (alarm)
    print(bug_report)
    return bug_report
