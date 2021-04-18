import json

WRITE_READ_FLAG = True
ERROR_FILTER = True
CROSS_BOUNDARY_FLAG = True
ONLY_DELETE = True

SONAR_EVENT_MARK = "[SONAR-EVENT]"
SONAR_SIDE_EFFECT_MARK = "[SONAR-SIDE-EFFECT]"
SONAR_CACHE_READ_MARK = "[SONAR-CACHE-READ]"
SONAR_START_RECONCILE_MARK = "[SONAR-START-RECONCILE]"
SONAR_FINISH_RECONCILE_MARK = "[SONAR-FINISH-RECONCILE]"
SONAR_EVENT_APPLIED_MARK = "[SONAR-EVENT-APPLIED]"

POD = "pod"
PVC = "persistentvolumeclaim"
DEPLOYMENT = "deployment"
STS = "statefulset"

KTYPES = [POD, PVC, DEPLOYMENT, STS]


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
    assert SONAR_EVENT_MARK in line
    tokens = line[line.find(SONAR_EVENT_MARK):].strip("\n").split("\t")
    return Event(tokens[1], tokens[2], tokens[3], json.loads(tokens[4]))


def parse_side_effect(line):
    assert SONAR_SIDE_EFFECT_MARK in line
    tokens = line[line.find(SONAR_SIDE_EFFECT_MARK):].strip(
        "\n").split("\t")
    return SideEffect(tokens[1], tokens[2], tokens[3], tokens[4], tokens[5])


def parse_cache_read(line):
    assert SONAR_CACHE_READ_MARK in line
    tokens = line[line.find(SONAR_CACHE_READ_MARK):].strip("\n").split("\t")
    if tokens[1] == "Get":
        return CacheRead(tokens[1], tokens[2], tokens[3], tokens[4], tokens[5])
    else:
        return CacheRead(tokens[1], tokens[2][:-4], "", "", tokens[3])


def parse_event_id_only(line):
    assert SONAR_EVENT_APPLIED_MARK in line or SONAR_EVENT_MARK in line
    if SONAR_EVENT_APPLIED_MARK in line:
        tokens = line[line.find(SONAR_EVENT_APPLIED_MARK):].strip(
            "\n").split("\t")
        return EventIDOnly(tokens[1])
    else:
        tokens = line[line.find(SONAR_EVENT_MARK):].strip("\n").split("\t")
        return EventIDOnly(tokens[1])
