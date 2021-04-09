import json
import yaml
import copy
import sys
import os
import shutil
import kubernetes
import controllers

CROSS_BOUNDARY_FLAG = True
WRITE_READ_FLAG = True
ERROR_FILTER = True
ONLY_DELETE = True

SONAR_EVENT_MARK = "[SONAR-EVENT]"
SONAR_SIDE_EFFECT_MARK = "[SONAR-SIDE-EFFECT]"
SONAR_CACHE_READ_MARK = "[SONAR-CACHE-READ]"
SONAR_START_RECONCILE_MARK = "[SONAR-START-RECONCILE]"
SONAR_FINISH_RECONCILE_MARK = "[SONAR-FINISH-RECONCILE]"
SONAR_RECORD_MARK = "[SONAR-RECORD]"

POD = "pod"
PVC = "persistentvolumeclaim"
DEPLOYMENT = "deployment"
STS = "statefulset"

ktypes = [POD, PVC, DEPLOYMENT, STS]


class Event:
    def __init__(self, id, etype, rtype, obj):
        self.id = id
        self.etype = etype
        self.rtype = rtype
        self.obj = obj
        self.key = self.rtype + "/" + \
            self.obj["metadata"]["namespace"] + \
            "/" + self.obj["metadata"]["name"]


class SideEffect:
    def __init__(self, etype, rtype, namespace, name, error):
        self.etype = etype
        self.rtype = rtype
        self.namespace = namespace
        self.name = name
        self.error = error


class CacheRead:
    def __init__(self, etype, rtype, namespace, name, error):
        self.etype = etype
        self.rtype = rtype
        self.namespace = namespace
        self.name = name
        self.error = error
        self.key = self.rtype + "/" + self.namespace + "/" + self.name


def parseEvent(line):
    assert SONAR_EVENT_MARK in line
    tokens = line[line.find(SONAR_EVENT_MARK):].strip("\n").split("\t")
    return Event(tokens[1], tokens[2], tokens[3], json.loads(tokens[4]))


def parseSideEffect(line):
    assert SONAR_SIDE_EFFECT_MARK in line
    tokens = line[line.find(SONAR_SIDE_EFFECT_MARK):].strip("\n").split("\t")
    return SideEffect(tokens[1], tokens[2], tokens[3], tokens[4], tokens[5])


def parseCacheRead(line):
    assert SONAR_CACHE_READ_MARK in line
    tokens = line[line.find(SONAR_CACHE_READ_MARK):].strip("\n").split("\t")
    if tokens[1] == "Get":
        return CacheRead(tokens[1], tokens[2], tokens[3], tokens[4], tokens[5])
    else:
        return CacheRead(tokens[1], tokens[2][:-4], "", "", tokens[3])


def generate_event_map(path):
    event_map = {}
    for line in open(path).readlines():
        if SONAR_EVENT_MARK not in line:
            continue
        event = parseEvent(line)
        if event.key not in event_map:
            event_map[event.key] = []
        event_map[event.key].append(event)
    return event_map


def event_read_intersect(event, cacheRead):
    if cacheRead.etype == "Get":
        return event.key == cacheRead.key
    else:
        return event.rtype == cacheRead.rtype


def affect_read(event, event_ts, reads_cur_round):
    for read_ts in reads_cur_round:
        if read_ts > event_ts and event_read_intersect(event, reads_cur_round[read_ts]):
            return True
    return False


def find_related_events(sideEffect, events_cur_round, events_prev_round, reads_cur_round):
    final_related_events = []
    related_events = list(events_cur_round.values())
    unrelated_events = set()
    if CROSS_BOUNDARY_FLAG:
        related_events.extend(list(events_prev_round.values()))
    if WRITE_READ_FLAG:
        for event_ts in events_prev_round:
            if not affect_read(events_prev_round[event_ts], event_ts, reads_cur_round):
                unrelated_events.add(events_prev_round[event_ts].id)
        for event_ts in events_cur_round:
            if not affect_read(events_cur_round[event_ts], event_ts, reads_cur_round):
                unrelated_events.add(events_cur_round[event_ts].id)
    for event in related_events:
        if event.id in unrelated_events:
            continue
        final_related_events.append(event)
    return final_related_events


def generate_causality_pairs(path):
    causality_pairs = []
    reads_cur_round = {}
    events_cur_round = {}
    events_prev_round = {}
    lines = open(path).readlines()
    for i in range(len(lines)):
        # we use the line number as the logic timestamp since all the logs are printed in the same thread
        line = lines[i]
        if SONAR_EVENT_MARK in line:
            events_cur_round[i] = parseEvent(line)
        elif SONAR_CACHE_READ_MARK in line:
            reads_cur_round[i] = parseCacheRead(line)
        elif SONAR_SIDE_EFFECT_MARK in line:
            side_effect = parseSideEffect(line)
            events = find_related_events(side_effect, events_cur_round,
                                         events_prev_round, reads_cur_round)
            causality_pairs.append([side_effect, events])
        elif SONAR_FINISH_RECONCILE_MARK in line:
            events_prev_round = copy.deepcopy(events_cur_round)
            events_cur_round = {}
    return causality_pairs


def find_previous_event(event, event_map):
    id = event.id
    key = event.key
    assert key in event_map, "invalid key %s, not found in event_map" % (key)
    for i in range(len(event_map[key])):
        if event_map[key][i].id == id:
            if i == 0:
                return None, event_map[key][i]
            else:
                return event_map[key][i-1], event_map[key][i]


def compressObject(prevObject, curObject, slimPrevObject, slimCurObject):
    toDel = []
    toDelCur = []
    toDelPrev = []
    allKeys = set(curObject.keys()).union(prevObject.keys())
    for key in allKeys:
        if key not in curObject:
            continue
        elif key not in prevObject:
            continue
        elif key == "resourceVersion" or key == "time" or key == "managedFields" or key == "lastTransitionTime" or key == "generation":
            toDel.append(key)
        elif str(curObject[key]) != str(prevObject[key]):
            if isinstance(curObject[key], dict):
                if not isinstance(prevObject[key], dict):
                    continue
                res = compressObject(
                    prevObject[key], curObject[key], slimPrevObject[key], slimCurObject[key])
                if res:
                    toDel.append(key)
            elif isinstance(curObject[key], list):
                if not isinstance(prevObject[key], list):
                    continue
                for i in range(len(curObject[key])):
                    if i >= len(prevObject[key]):
                        break
                    elif str(curObject[key][i]) != str(prevObject[key][i]):
                        if isinstance(curObject[key][i], dict):
                            if not isinstance(prevObject[key][i], dict):
                                continue
                            res = compressObject(
                                prevObject[key][i], curObject[key][i], slimPrevObject[key][i], slimCurObject[key][i])
                            if res:
                                # SONAR_SKIP means we can skip the value in list when later comparing to the events in testing run
                                slimCurObject[key][i] = "SONAR-SKIP"
                                slimPrevObject[key][i] = "SONAR-SKIP"
                        elif isinstance(curObject[key][i], list):
                            assert False
                        else:
                            continue
                    else:
                        slimCurObject[key][i] = "SONAR-SKIP"
                        slimPrevObject[key][i] = "SONAR-SKIP"
            else:
                continue
        else:
            toDel.append(key)
    for key in toDel:
        del slimCurObject[key]
        del slimPrevObject[key]
    for key in slimCurObject:
        if isinstance(slimCurObject[key], dict):
            if len(slimCurObject[key]) == 0:
                toDelCur.append(key)
    for key in slimPrevObject:
        if isinstance(slimPrevObject[key], dict):
            if len(slimPrevObject[key]) == 0:
                toDelPrev.append(key)
    for key in toDelCur:
        del slimCurObject[key]
    for key in toDelPrev:
        del slimPrevObject[key]
    if len(slimCurObject) == 0 and len(slimPrevObject) == 0:
        return True
    return False


def diffEvents(prevEvent, curEvent):
    prevObject = prevEvent.obj
    curObject = curEvent.obj
    slimPrevObject = copy.deepcopy(prevObject)
    slimCurObject = copy.deepcopy(curObject)
    compressObject(prevObject, curObject, slimPrevObject, slimCurObject)
    return slimPrevObject, slimCurObject


def canonicalization(event):
    for key in event:
        if isinstance(event[key], dict):
            canonicalization(event[key])
        else:
            if "time" in key.lower():
                event[key] = "SONAR-EXIST"
    return event


def generate_triggering_points(event_map, causality_pairs):
    triggering_points = []
    for pair in causality_pairs:
        side_effect = pair[0]
        if ERROR_FILTER:
            if side_effect.error == "NotFound":
                continue
        events = pair[1]
        for event in events:
            prev_event, cur_event = find_previous_event(event, event_map)
            triggering_point = {"name": cur_event.obj["metadata"]["name"],
                                "namespace": cur_event.obj["metadata"]["namespace"],
                                "rtype": cur_event.rtype,
                                "effect": side_effect.__dict__}
            if prev_event is None:
                triggering_point["ttype"] = "todo"
            elif prev_event.etype != cur_event.etype:
                triggering_point["ttype"] = "todo"
            else:
                slim_prev_obj, slim_cur_obj = diffEvents(
                    prev_event, cur_event)
                triggering_point["ttype"] = "event-delta"
                triggering_point["prevEvent"] = slim_prev_obj
                triggering_point["curEvent"] = slim_cur_obj
                triggering_point["prevEventType"] = prev_event.etype
                triggering_point["curEventType"] = cur_event.etype
            triggering_points.append(triggering_point)
    return triggering_points


def timeTravelDescription(yamlMap):
    return "Pause %s after it processes a %s event E. "\
        "E should match the pattern %s and the events before E should match %s. "\
        "And restart the controller %s after %s processes a %s %s event." % (
            yamlMap["straggler"], "/".join([yamlMap["ce-namespace"],
                                           yamlMap["ce-rtype"], yamlMap["ce-name"]]),
            yamlMap["ce-diff-current"], yamlMap["ce-diff-previous"], yamlMap["operator-pod"],
            yamlMap["front-runner"], yamlMap["se-etype"], "/".join([yamlMap["se-namespace"],
                                                                    yamlMap["se-rtype"], yamlMap["se-name"]]))


def generateTimaTravelYaml(triggeringPoints, path, project, timing="after"):
    yamlMap = {}
    yamlMap["project"] = project
    yamlMap["mode"] = "time-travel"
    yamlMap["straggler"] = "kind-control-plane3"
    yamlMap["front-runner"] = "kind-control-plane"
    yamlMap["operator-pod"] = project
    yamlMap["command"] = controllers.command[project]
    yamlMap["timing"] = timing
    i = 0
    for triggeringPoint in triggeringPoints:
        if triggeringPoint["ttype"] != "event-delta":
            # TODO: handle the single event trigger
            continue
        effect = triggeringPoint["effect"]
        # TODO: consider update side effects and even app-specific side effects
        if effect["etype"] != "Delete" and (ONLY_DELETE or effect["etype"] != "Create"):
            continue
        i += 1
        yamlMap["ce-name"] = triggeringPoint["name"]
        yamlMap["ce-namespace"] = triggeringPoint["namespace"]
        yamlMap["ce-rtype"] = triggeringPoint["rtype"]
        yamlMap["ce-diff-current"] = json.dumps(
            canonicalization(copy.deepcopy(triggeringPoint["curEvent"])))
        yamlMap["ce-diff-previous"] = json.dumps(
            canonicalization(copy.deepcopy(triggeringPoint["prevEvent"])))
        yamlMap["ce-etype-current"] = triggeringPoint["curEventType"]
        yamlMap["ce-etype-previous"] = triggeringPoint["prevEventType"]
        yamlMap["se-name"] = effect["name"]
        yamlMap["se-namespace"] = effect["namespace"]
        yamlMap["se-rtype"] = effect["rtype"]
        yamlMap["se-etype"] = "ADDED" if effect["etype"] == "Delete" else "DELETED"
        yamlMap["description"] = timeTravelDescription(yamlMap)
        yaml.dump(yamlMap, open(
            os.path.join(path, "%s-%s.yaml" % (str(i), timing)), "w"), sort_keys=False)
    print("Generated %d time-travel configs" % i)


def generateDigest(path):
    digest = {}
    empty_entry = {"size": -1, "terminating": -1,
                   "create": 0, "update": 0, "delete": 0}
    for line in open(path).readlines():
        if SONAR_SIDE_EFFECT_MARK not in line:
            continue
        line = line[line.find(SONAR_SIDE_EFFECT_MARK):].strip("\n")
        tokens = line.split("\t")
        effectType = tokens[1].lower()
        # if effectType == "update":
        #     continue
        rType = tokens[2]
        if rType not in digest:
            digest[rType] = copy.deepcopy(empty_entry)
        digest[rType][effectType] += 1

    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    apps_v1 = kubernetes.client.AppsV1Api()
    k8s_namespace = "default"
    resources = {}
    for ktype in ktypes:
        resources[ktype] = []
        if ktype not in digest:
            digest[ktype] = copy.deepcopy(empty_entry)
    for pod in core_v1.list_namespaced_pod(k8s_namespace, watch=False).items:
        resources[POD].append(pod)
    for pvc in core_v1.list_namespaced_persistent_volume_claim(k8s_namespace, watch=False).items:
        resources[PVC].append(pvc)
    for dp in apps_v1.list_namespaced_deployment(k8s_namespace, watch=False).items:
        resources[DEPLOYMENT].append(dp)
    for sts in apps_v1.list_namespaced_stateful_set(k8s_namespace, watch=False).items:
        resources[STS].append(sts)
    for ktype in ktypes:
        digest[ktype]["size"] = len(resources[ktype])
        terminating = 0
        for item in resources[ktype]:
            if item.metadata.deletion_timestamp != None:
                terminating += 1
        digest[ktype]["terminating"] = terminating
    return digest


def dump_files(dir, event_map, causality_pairs, digest, triggeringPoints):
    json_dir = os.path.join(dir, "generated-json")
    if os.path.exists(json_dir):
        shutil.rmtree(json_dir)
    os.makedirs(json_dir, exist_ok=True)
    # json.dump(event_map, open(os.path.join(
    #     json_dir, "event-map.json"), "w"), indent=4)
    # json.dump(causality_pairs, open(os.path.join(
    #     json_dir, "causality-pairs.json"), "w"), indent=4)
    json.dump(digest, open(os.path.join(
        dir, "digest.json"), "w"), indent=4)
    json.dump(triggeringPoints, open(os.path.join(
        json_dir, "triggering-points.json"), "w"), indent=4)


def analyzeTrace(project, dir, double_sides=False):
    log_path = os.path.join(dir, "sonar-server.log")
    conf_dir = os.path.join(dir, "generated-config")
    if os.path.exists(conf_dir):
        shutil.rmtree(conf_dir)
    os.makedirs(conf_dir, exist_ok=True)
    event_map = generate_event_map(log_path)
    causality_pairs = generate_causality_pairs(log_path)
    digest = generateDigest(log_path)
    triggeringPoints = generate_triggering_points(event_map, causality_pairs)
    dump_files(dir, event_map, causality_pairs, digest, triggeringPoints)
    generateTimaTravelYaml(triggeringPoints, conf_dir, project)
    if double_sides:
        generateTimaTravelYaml(triggeringPoints, conf_dir, project, "before")


if __name__ == "__main__":
    project = sys.argv[1]
    test = sys.argv[2]
    dir = os.path.join("log", project, test, "learn")
    analyzeTrace(project, dir)
