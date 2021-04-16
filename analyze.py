import json
import yaml
import copy
import sys
import os
import shutil
import kubernetes
import controllers
import constant


class Event:
    def __init__(self, id, etype, rtype, obj):
        self.id = id
        self.etype = etype
        self.rtype = rtype
        self.obj = obj
        # TODO: In some case the metadata doesn't carry in namespace field, may dig into that later
        self.namespace = self.obj["metadata"]["namespace"] if "namespace" in self.obj["metadata"] else "default"
        self.key = self.rtype + "/" + \
            self.namespace + \
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


class EventIDOnly:
    def __init__(self, id):
        self.id = id


def parse_event(line):
    assert constant.SONAR_EVENT_MARK in line
    tokens = line[line.find(constant.SONAR_EVENT_MARK):].strip("\n").split("\t")
    return Event(tokens[1], tokens[2], tokens[3], json.loads(tokens[4]))


def parse_side_effect(line):
    assert constant.SONAR_SIDE_EFFECT_MARK in line
    tokens = line[line.find(constant.SONAR_SIDE_EFFECT_MARK):].strip(
        "\n").split("\t")
    return SideEffect(tokens[1], tokens[2], tokens[3], tokens[4], tokens[5])


def parse_cache_read(line):
    assert constant.SONAR_CACHE_READ_MARK in line
    tokens = line[line.find(constant.SONAR_CACHE_READ_MARK):].strip("\n").split("\t")
    if tokens[1] == "Get":
        return CacheRead(tokens[1], tokens[2], tokens[3], tokens[4], tokens[5])
    else:
        return CacheRead(tokens[1], tokens[2][:-4], "", "", tokens[3])


def parse_event_id_only(line):
    assert constant.SONAR_EVENT_APPLIED_MARK in line or constant.SONAR_EVENT_MARK in line
    if constant.SONAR_EVENT_APPLIED_MARK in line:
        tokens = line[line.find(constant.SONAR_EVENT_APPLIED_MARK):].strip(
            "\n").split("\t")
        return EventIDOnly(tokens[1])
    else:
        tokens = line[line.find(constant.SONAR_EVENT_MARK):].strip("\n").split("\t")
        return EventIDOnly(tokens[1])


def generate_event_map(path):
    event_map = {}
    event_id_map = {}
    for line in open(path).readlines():
        if constant.SONAR_EVENT_MARK not in line:
            continue
        event = parse_event(line)
        if event.key not in event_map:
            event_map[event.key] = []
        event_map[event.key].append(event)
        event_id_map[event.id] = event
    return event_map, event_id_map


def event_read_intersect(event_id_map, event_id, cacheRead):
    if cacheRead.etype == "Get":
        return event_id_map[event_id].key == cacheRead.key
    else:
        return event_id_map[event_id].rtype == cacheRead.rtype


def affect_read(event_id_map, event_id, event_ts, reads_cur_round):
    for read_ts in reads_cur_round:
        if read_ts > event_ts and event_read_intersect(event_id_map, event_id, reads_cur_round[read_ts]):
            return True
    return False


def find_related_events(event_id_map, sideEffect, events_cur_round, events_prev_round, reads_cur_round, events_applied_cur_round, events_applied_prev_round):
    final_related_events = []
    related_events = set(events_cur_round.values())
    unrelated_events = set()
    if constant.CROSS_BOUNDARY_FLAG:
        related_events.update(set(events_applied_prev_round.values()))
        related_events.update(set(events_prev_round.values()))
    if constant.WRITE_READ_FLAG:
        for event_ts in events_prev_round:
            if not affect_read(event_id_map, events_prev_round[event_ts], event_ts, reads_cur_round):
                unrelated_events.add(events_prev_round[event_ts])
        for event_ts in events_cur_round:
            if not affect_read(event_id_map, events_cur_round[event_ts], event_ts, reads_cur_round):
                unrelated_events.add(events_cur_round[event_ts])
    for event_id in related_events:
        if event_id in unrelated_events:
            continue
        final_related_events.append(event_id_map[event_id])
    return final_related_events


def generate_causality_pairs(path, event_id_map):
    causality_pairs = []
    reads_cur_round = {}
    events_cur_round = {}
    events_prev_round = {}
    events_applied_cur_round = {}
    events_applied_prev_round = {}
    lines = open(path).readlines()
    for i in range(len(lines)):
        # we use the line number as the logic timestamp since all the logs are printed in the same thread
        line = lines[i]
        if constant.SONAR_EVENT_MARK in line:
            events_cur_round[i] = parse_event_id_only(line).id
        elif constant.SONAR_EVENT_APPLIED_MARK in line:
            events_applied_cur_round[i] = parse_event_id_only(line).id
        elif constant.SONAR_CACHE_READ_MARK in line:
            reads_cur_round[i] = parse_cache_read(line)
        elif constant.SONAR_SIDE_EFFECT_MARK in line:
            side_effect = parse_side_effect(line)
            events = find_related_events(event_id_map, side_effect,
                                         events_cur_round, events_prev_round,
                                         reads_cur_round,
                                         events_applied_cur_round, events_applied_prev_round)
            causality_pairs.append([side_effect, events])
        elif constant.SONAR_FINISH_RECONCILE_MARK in line:
            events_prev_round = copy.deepcopy(events_cur_round)
            events_cur_round = {}
            events_applied_prev_round = copy.deepcopy(events_applied_cur_round)
            events_applied_cur_round = {}
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


def compress_object(prev_object, cur_object, slim_prev_object, slim_cur_object):
    to_del = []
    to_del_cur = []
    to_del_prev = []
    allKeys = set(cur_object.keys()).union(prev_object.keys())
    for key in allKeys:
        if key not in cur_object:
            continue
        elif key not in prev_object:
            continue
        elif key == "resourceVersion" or key == "time" or key == "managedFields" or key == "lastTransitionTime" or key == "generation":
            to_del.append(key)
        elif str(cur_object[key]) != str(prev_object[key]):
            if isinstance(cur_object[key], dict):
                if not isinstance(prev_object[key], dict):
                    continue
                res = compress_object(
                    prev_object[key], cur_object[key], slim_prev_object[key], slim_cur_object[key])
                if res:
                    to_del.append(key)
            elif isinstance(cur_object[key], list):
                if not isinstance(prev_object[key], list):
                    continue
                for i in range(len(cur_object[key])):
                    if i >= len(prev_object[key]):
                        break
                    elif str(cur_object[key][i]) != str(prev_object[key][i]):
                        if isinstance(cur_object[key][i], dict):
                            if not isinstance(prev_object[key][i], dict):
                                continue
                            res = compress_object(
                                prev_object[key][i], cur_object[key][i], slim_prev_object[key][i], slim_cur_object[key][i])
                            if res:
                                # SONAR_SKIP means we can skip the value in list when later comparing to the events in testing run
                                slim_cur_object[key][i] = "SONAR-SKIP"
                                slim_prev_object[key][i] = "SONAR-SKIP"
                        elif isinstance(cur_object[key][i], list):
                            assert False
                        else:
                            continue
                    else:
                        slim_cur_object[key][i] = "SONAR-SKIP"
                        slim_prev_object[key][i] = "SONAR-SKIP"
            else:
                continue
        else:
            to_del.append(key)
    for key in to_del:
        del slim_cur_object[key]
        del slim_prev_object[key]
    for key in slim_cur_object:
        if isinstance(slim_cur_object[key], dict):
            if len(slim_cur_object[key]) == 0:
                to_del_cur.append(key)
    for key in slim_prev_object:
        if isinstance(slim_prev_object[key], dict):
            if len(slim_prev_object[key]) == 0:
                to_del_prev.append(key)
    for key in to_del_cur:
        del slim_cur_object[key]
    for key in to_del_prev:
        del slim_prev_object[key]
    if len(slim_cur_object) == 0 and len(slim_prev_object) == 0:
        return True
    return False


def diff_events(prevEvent, curEvent):
    prev_object = prevEvent.obj
    cur_object = curEvent.obj
    slim_prev_object = copy.deepcopy(prev_object)
    slim_cur_object = copy.deepcopy(cur_object)
    compress_object(prev_object, cur_object, slim_prev_object, slim_cur_object)
    return slim_prev_object, slim_cur_object


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
        if constant.ERROR_FILTER:
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
            # elif prev_event.etype != cur_event.etype:
            #     triggering_point["ttype"] = "todo"
            else:
                slim_prev_obj, slim_cur_obj = diff_events(
                    prev_event, cur_event)
                triggering_point["ttype"] = "event-delta"
                triggering_point["prevEvent"] = slim_prev_obj
                triggering_point["curEvent"] = slim_cur_obj
                triggering_point["prevEventType"] = prev_event.etype
                triggering_point["curEventType"] = cur_event.etype
            triggering_points.append(triggering_point)
    return triggering_points


def time_travel_description(yaml_map):
    return "Pause %s after it processes a %s event E. "\
        "E should match the pattern %s and the events before E should match %s. "\
        "And restart the controller %s after %s processes a %s %s event." % (
            yaml_map["straggler"], "/".join([yaml_map["ce-namespace"],
                                             yaml_map["ce-rtype"], yaml_map["ce-name"]]),
            yaml_map["ce-diff-current"], yaml_map["ce-diff-previous"], yaml_map["operator-pod"],
            yaml_map["front-runner"], yaml_map["se-etype"], "/".join([yaml_map["se-namespace"],
                                                                      yaml_map["se-rtype"], yaml_map["se-name"]]))


def generate_time_travel_yaml(triggering_points, path, project, timing="after"):
    yaml_map = {}
    yaml_map["project"] = project
    yaml_map["mode"] = "time-travel"
    yaml_map["straggler"] = "kind-control-plane3"
    yaml_map["front-runner"] = "kind-control-plane"
    yaml_map["operator-pod"] = project
    yaml_map["command"] = controllers.command[project]
    yaml_map["timing"] = timing
    suffix = "-b" if timing == "before" else ""
    i = 0
    for triggering_point in triggering_points:
        if triggering_point["ttype"] != "event-delta":
            # TODO: handle the single event trigger
            continue
        effect = triggering_point["effect"]
        # TODO: consider update side effects and even app-specific side effects
        if effect["etype"] != "Delete" and (constant.ONLY_DELETE or effect["etype"] != "Create"):
            continue
        i += 1
        yaml_map["ce-name"] = triggering_point["name"]
        yaml_map["ce-namespace"] = triggering_point["namespace"]
        yaml_map["ce-rtype"] = triggering_point["rtype"]
        yaml_map["ce-diff-current"] = json.dumps(
            canonicalization(copy.deepcopy(triggering_point["curEvent"])))
        yaml_map["ce-diff-previous"] = json.dumps(
            canonicalization(copy.deepcopy(triggering_point["prevEvent"])))
        yaml_map["ce-etype-current"] = triggering_point["curEventType"]
        yaml_map["ce-etype-previous"] = triggering_point["prevEventType"]
        yaml_map["se-name"] = effect["name"]
        yaml_map["se-namespace"] = effect["namespace"]
        yaml_map["se-rtype"] = effect["rtype"]
        yaml_map["se-etype"] = "ADDED" if effect["etype"] == "Delete" else "DELETED"
        yaml_map["description"] = time_travel_description(yaml_map)
        yaml.dump(yaml_map, open(
            os.path.join(path, "time-travel-%s%s.yaml" % (str(i), suffix)), "w"), sort_keys=False)
    print("Generated %d time-travel config(s) in %s" % (i, path))


def generate_digest(path):
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
    return side_effect, status


def dump_files(dir, event_map, causality_pairs, side_effect, status, triggering_points):
    json_dir = os.path.join(dir, "generated-json")
    if os.path.exists(json_dir):
        shutil.rmtree(json_dir)
    os.makedirs(json_dir, exist_ok=True)
    json.dump(side_effect, open(os.path.join(
        dir, "side-effect.json"), "w"), indent=4, sort_keys=True)
    json.dump(status, open(os.path.join(
        dir, "status.json"), "w"), indent=4, sort_keys=True)
    json.dump(triggering_points, open(os.path.join(
        json_dir, "triggering-points.json"), "w"), indent=4)


def analyze_trace(project, dir, double_sides=False):
    log_path = os.path.join(dir, "sonar-server.log")
    conf_dir = os.path.join(dir, "generated-config")
    if os.path.exists(conf_dir):
        shutil.rmtree(conf_dir)
    os.makedirs(conf_dir, exist_ok=True)
    event_map, event_id_map = generate_event_map(log_path)
    causality_pairs = generate_causality_pairs(log_path, event_id_map)
    side_effect, status = generate_digest(log_path)
    triggering_points = generate_triggering_points(event_map, causality_pairs)
    dump_files(dir, event_map, causality_pairs,
               side_effect, status, triggering_points)
    generate_time_travel_yaml(triggering_points, conf_dir, project)
    if double_sides:
        generate_time_travel_yaml(
            triggering_points, conf_dir, project, "before")


if __name__ == "__main__":
    project = sys.argv[1]
    test = sys.argv[2]
    dir = os.path.join("log", project, test, "learn")
    analyze_trace(project, dir)
