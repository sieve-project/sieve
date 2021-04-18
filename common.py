import json
import re

WRITE_READ_FILTER_FLAG = True
ERROR_MSG_FILTER_FLAG = True
# TODO: for now, only consider Delete
INTERESTING_SIDE_EFFECT_TYPE = ["Delete"]
FILTERED_ERROR_TYPE = ["NotFound"]

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

BORING_EVENT_OBJECT_FIELDS = ["resourceVersion", "time",
                              "managedFields", "lastTransitionTime", "generation"]
SONAR_SKIP_MARKER = "SONAR-SKIP"
SONAR_CANONICALIZATION_MARKER = "SONAR-EXIST"
TIME_REG = '^[0-9]+-[0-9]+-[0-9]+T[0-9]+:[0-9]+:[0-9]+Z$'


class Event:
    def __init__(self, id, etype, rtype, obj):
        self.id = id
        self.etype = etype
        self.rtype = rtype
        self.obj = obj
        # TODO(Wenqing): In some case the metadata doesn't carry in namespace field, may dig into that later
        self.namespace = self.obj["metadata"]["namespace"] if "namespace" in self.obj["metadata"] else "default"
        self.name = self.obj["metadata"]["name"]
        self.start_timestamp = -1
        self.end_timestamp = -1
        self.key = self.rtype + "/" + self.namespace + "/" + self.name

    def set_start_timestamp(self, start_timestamp):
        self.start_timestamp = start_timestamp

    def set_end_timestamp(self, end_timestamp):
        self.end_timestamp = end_timestamp


class SideEffect:
    def __init__(self, etype, rtype, namespace, name, error):
        self.etype = etype
        self.rtype = rtype
        self.namespace = namespace
        self.name = name
        self.error = error
        self.end_timestamp = -1
        self.read_types = set()
        self.read_keys = set()
        self.range_start_timestamp = -1
        self.range_end_timestamp = -1
        self.in_first_reconcile = False
        self.owner_controllers = set()

    def to_dict(self):
        side_effect_as_dict = {}
        side_effect_as_dict["etype"] = self.etype
        side_effect_as_dict["rtype"] = self.rtype
        side_effect_as_dict["namespace"] = self.namespace
        side_effect_as_dict["name"] = self.name
        side_effect_as_dict["error"] = self.error
        return side_effect_as_dict

    def set_in_first_reconcile(self, in_first_reconcile):
        self.in_first_reconcile = in_first_reconcile

    def set_end_timestamp(self, end_timestamp):
        self.end_timestamp = end_timestamp

    def set_read_types(self, read_types):
        self.read_types = read_types

    def set_read_keys(self, read_keys):
        self.read_keys = read_keys

    def set_range(self, start_timestamp, end_timestamp):
        self.range_start_timestamp = start_timestamp
        self.range_end_timestamp = end_timestamp

    def range_overlap(self, event):
        assert self.range_start_timestamp != -1
        assert self.range_end_timestamp != -1
        assert event.start_timestamp != -1
        if self.in_first_reconcile:
            # the side effect is in the first reconcile and there is no prev reconcile;
            # return true when event starts eariler than side effect ends
            return self.range_end_timestamp > event.start_timestamp
        else:
            if event.end_timestamp == -1:
                # we have not met the end of the event; return true when event starts eariler than side effect ends
                return self.range_end_timestamp > event.start_timestamp
            else:
                # return true when event ends later than the prev reconcile start and event starts eariler than side effect ends
                return self.range_start_timestamp < event.end_timestamp and self.range_end_timestamp > event.start_timestamp

    def interest_overlap(self, event):
        return event.key in self.read_keys or event.rtype in self.read_types


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
