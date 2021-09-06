import json
import sieve_config

WRITE_READ_FILTER_FLAG = True
ERROR_MSG_FILTER_FLAG = True
# TODO: for now, only consider Delete
DELETE_ONLY_FILTER_FLAG = True
FILTERED_ERROR_TYPE = ["NotFound", "Conflict"]
ALLOWED_ERROR_TYPE = ["NoError"]

SIEVE_BEFORE_EVENT_MARK = "[SIEVE-BEFORE-EVENT]"
SIEVE_AFTER_EVENT_MARK = "[SIEVE-AFTER-EVENT]"
SIEVE_AFTER_SIDE_EFFECT_MARK = "[SIEVE-AFTER-SIDE-EFFECT]"
SIEVE_AFTER_READ_MARK = "[SIEVE-AFTER-READ]"
SIEVE_BEFORE_RECONCILE_MARK = "[SIEVE-BEFORE-RECONCILE]"
SIEVE_AFTER_RECONCILE_MARK = "[SIEVE-AFTER-RECONCILE]"

BORING_EVENT_OBJECT_FIELDS = ["resourceVersion", "time",
                              "managedFields", "lastTransitionTime", "generation", "annotations", "deletionGracePeriodSeconds"]

SIEVE_SKIP_MARKER = "SIEVE-SKIP"
SIEVE_CANONICALIZATION_MARKER = "SIEVE-NON-NIL"

TIME_REG = '^[0-9]+-[0-9]+-[0-9]+T[0-9]+:[0-9]+:[0-9]+Z$'
IP_REG = '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'


def translate_side_effect(side_effect, reverse=False):
    if side_effect == "ADDED":
        return "deletion" if reverse else "creation"
    elif side_effect == "DELETED":
        return "creation" if reverse else "deletion"
    else:
        assert False


class Event:
    def __init__(self, id, etype, rtype, obj):
        # make the id integer to keep consistent with SideEffect
        self.id = int(id)
        self.etype = etype
        self.rtype = rtype
        self.obj = obj
        # TODO(Wenqing): In some case the metadata doesn't carry in namespace field, may dig into that later
        self.namespace = self.obj["metadata"]["namespace"] if "namespace" in self.obj[
            "metadata"] else sieve_config.config["namespace"]
        self.name = self.obj["metadata"]["name"]
        self.start_timestamp = -1
        self.end_timestamp = -1
        self.key = self.rtype + "/" + self.namespace + "/" + self.name

    def set_start_timestamp(self, start_timestamp):
        self.start_timestamp = start_timestamp

    def set_end_timestamp(self, end_timestamp):
        self.end_timestamp = end_timestamp


class SideEffect:
    side_effect_cnt = 0

    def __init__(self, etype, rtype, namespace, name, error, obj):
        self.id = SideEffect.side_effect_cnt
        SideEffect.side_effect_cnt += 1
        self.etype = etype
        self.rtype = rtype
        self.namespace = namespace
        self.name = name
        self.error = error
        self.obj = obj
        self.end_timestamp = -1
        self.read_types = set()
        self.read_keys = set()
        self.range_start_timestamp = -1
        self.range_end_timestamp = -1
        self.owner_controllers = set()
        self.key = self.rtype + "/" + self.namespace + "/" + self.name

    def to_dict(self):
        side_effect_as_dict = {}
        side_effect_as_dict["etype"] = self.etype
        side_effect_as_dict["rtype"] = self.rtype
        side_effect_as_dict["namespace"] = self.namespace
        side_effect_as_dict["name"] = self.name
        side_effect_as_dict["error"] = self.error
        return side_effect_as_dict

    def set_end_timestamp(self, end_timestamp):
        self.end_timestamp = end_timestamp

    def set_read_types(self, read_types):
        self.read_types = read_types

    def set_read_keys(self, read_keys):
        self.read_keys = read_keys

    def set_range(self, start_timestamp, end_timestamp):
        assert start_timestamp < end_timestamp
        self.range_start_timestamp = start_timestamp
        self.range_end_timestamp = end_timestamp

    def range_overlap(self, event):
        # This is the key method to generate the (event, side_effect) pairs
        assert self.range_end_timestamp != -1
        assert event.start_timestamp != -1
        assert event.end_timestamp != -1
        assert self.range_start_timestamp < self.range_end_timestamp
        assert event.start_timestamp < event.end_timestamp
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
        # make the id integer to keep consistent with SideEffect
        self.id = int(id)


class Reconcile:
    def __init__(self, controller_name, round_id):
        self.controller_name = controller_name
        self.round_id = round_id


def parse_event(line):
    assert SIEVE_BEFORE_EVENT_MARK in line
    tokens = line[line.find(SIEVE_BEFORE_EVENT_MARK):].strip("\n").split("\t")
    return Event(tokens[1], tokens[2], tokens[3], json.loads(tokens[4]))


def parse_side_effect(line):
    assert SIEVE_AFTER_SIDE_EFFECT_MARK in line
    tokens = line[line.find(SIEVE_AFTER_SIDE_EFFECT_MARK):].strip(
        "\n").split("\t")
    return SideEffect(tokens[1], tokens[2], tokens[3], tokens[4], tokens[5], tokens[6])


def parse_cache_read(line):
    assert SIEVE_AFTER_READ_MARK in line
    tokens = line[line.find(SIEVE_AFTER_READ_MARK):].strip("\n").split("\t")
    if tokens[1] == "Get":
        return CacheRead(tokens[1], tokens[2], tokens[3], tokens[4], tokens[5])
    else:
        return CacheRead(tokens[1], tokens[2][:-4], "", "", tokens[3])


def parse_event_id_only(line):
    assert SIEVE_AFTER_EVENT_MARK in line or SIEVE_BEFORE_EVENT_MARK in line
    if SIEVE_AFTER_EVENT_MARK in line:
        tokens = line[line.find(SIEVE_AFTER_EVENT_MARK):].strip(
            "\n").split("\t")
        return EventIDOnly(tokens[1])
    else:
        tokens = line[line.find(SIEVE_BEFORE_EVENT_MARK):].strip("\n").split("\t")
        return EventIDOnly(tokens[1])


def parse_reconcile(line):
    assert SIEVE_BEFORE_RECONCILE_MARK in line or SIEVE_AFTER_RECONCILE_MARK in line
    if SIEVE_BEFORE_RECONCILE_MARK in line:
        tokens = line[line.find(SIEVE_BEFORE_RECONCILE_MARK):].strip(
            "\n").split("\t")
        return Reconcile(tokens[1], tokens[2])
    else:
        tokens = line[line.find(SIEVE_AFTER_RECONCILE_MARK):].strip(
            "\n").split("\t")
        return Reconcile(tokens[1], tokens[2])
