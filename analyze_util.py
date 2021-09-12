import json
from typing import List
import sieve_config

WRITE_READ_FILTER_FLAG = True
ERROR_MSG_FILTER_FLAG = True
# TODO: for now, only consider Delete
DELETE_ONLY_FILTER_FLAG = True
FILTERED_ERROR_TYPE = ["NotFound", "Conflict"]
ALLOWED_ERROR_TYPE = ["NoError"]

SIEVE_BEFORE_EVENT_MARK = "[SIEVE-BEFORE-EVENT]"
SIEVE_AFTER_EVENT_MARK = "[SIEVE-AFTER-EVENT]"
SIEVE_BEFORE_SIDE_EFFECT_MARK = "[SIEVE-BEFORE-SIDE-EFFECT]"
SIEVE_AFTER_SIDE_EFFECT_MARK = "[SIEVE-AFTER-SIDE-EFFECT]"
SIEVE_AFTER_READ_MARK = "[SIEVE-AFTER-READ]"
SIEVE_BEFORE_RECONCILE_MARK = "[SIEVE-BEFORE-RECONCILE]"
SIEVE_AFTER_RECONCILE_MARK = "[SIEVE-AFTER-RECONCILE]"

BORING_EVENT_OBJECT_FIELDS = ["resourceVersion", "time",
                              "managedFields", "lastTransitionTime", "generation", "annotations", "deletionGracePeriodSeconds"]

SIEVE_SKIP_MARKER = "SIEVE-SKIP"
SIEVE_CANONICALIZATION_MARKER = "SIEVE-NON-NIL"

TIME_REG = "^[0-9]+-[0-9]+-[0-9]+T[0-9]+:[0-9]+:[0-9]+Z$"
IP_REG = "^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"

INTRA_THREAD_EDGE = "INTRA-THREAD"
INTER_THREAD_EDGE = "INTER-THREADS"


def consistent_type(event_type, side_effect_type):
    both_create = event_type == "Added" and side_effect_type == "Create"
    both_update = event_type == "Updated" and side_effect_type == "Update"
    both_delete = event_type == "Deleted" and side_effect_type == "Delete"
    return both_create or both_update or both_delete


def extract_namespace_name(obj):
    assert "metadata" in obj, "missing metadata in: " + str(obj)
    # TODO(Wenqing): Sometimes metadata doesn't carry namespace field, may dig into that later
    obj_name = obj["metadata"]["name"]
    obj_namespace = (
        obj["metadata"]["namespace"]
        if "namespace" in obj["metadata"]
        else sieve_config.config["namespace"]
    )
    return obj_namespace, obj_name


class Event:
    def __init__(self, id, etype, rtype, obj_str):
        self.id = int(id)
        self.etype = etype
        self.rtype = rtype
        self.obj_str = obj_str
        self.obj = json.loads(obj_str)
        self.namespace, self.name = extract_namespace_name(self.obj)
        self.start_timestamp = -1
        self.end_timestamp = -1
        self.key = self.rtype + "/" + self.namespace + "/" + self.name

    def set_start_timestamp(self, start_timestamp):
        self.start_timestamp = start_timestamp

    def set_end_timestamp(self, end_timestamp):
        self.end_timestamp = end_timestamp


class SideEffect:
    def __init__(self, id, etype, rtype, error, obj_str):
        self.id = int(id)
        self.etype = etype
        self.rtype = rtype
        self.error = error
        self.obj_str = obj_str
        self.obj = json.loads(obj_str)
        self.namespace, self.name = extract_namespace_name(self.obj)
        self.start_timestamp = -1
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

    def set_start_timestamp(self, start_timestamp):
        self.start_timestamp = start_timestamp

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
        self.id = int(id)


class SideEffectIDOnly:
    def __init__(self, id):
        self.id = int(id)


class Reconcile:
    def __init__(self, controller_name, round_id):
        self.controller_name = controller_name
        self.round_id = round_id


class EventsDataStructure:
    def __init__(self, event_list, event_key_map, event_id_map):
        self.event_list = event_list
        self.event_key_map = event_key_map
        self.event_id_map = event_id_map


class SideEffectsDataStructure:
    def __init__(self, side_effect_list, side_effect_id_map):
        self.side_effect_list = side_effect_list
        self.side_effect_id_map = side_effect_id_map


def parse_event(line):
    assert SIEVE_BEFORE_EVENT_MARK in line
    tokens = line[line.find(SIEVE_BEFORE_EVENT_MARK):].strip("\n").split("\t")
    return Event(tokens[1], tokens[2], tokens[3], tokens[4])


def parse_side_effect(line):
    assert SIEVE_AFTER_SIDE_EFFECT_MARK in line
    tokens = line[line.find(SIEVE_AFTER_SIDE_EFFECT_MARK)
                            :].strip("\n").split("\t")
    return SideEffect(tokens[1], tokens[2], tokens[3], tokens[4], tokens[5])


def parse_cache_read(line):
    assert SIEVE_AFTER_READ_MARK in line
    tokens = line[line.find(SIEVE_AFTER_READ_MARK):].strip("\n").split("\t")
    if tokens[1] == "Get":
        return CacheRead(tokens[1], tokens[2], tokens[3], tokens[4], tokens[5])
    else:
        # When using List, the resource type is like xxxlist so we need to trim the last four characters here
        assert tokens[2].endswith("list")
        return CacheRead(tokens[1], tokens[2][:-4], "", "", tokens[3])


def parse_event_id_only(line):
    assert SIEVE_AFTER_EVENT_MARK in line or SIEVE_BEFORE_EVENT_MARK in line
    if SIEVE_AFTER_EVENT_MARK in line:
        tokens = line[line.find(SIEVE_AFTER_EVENT_MARK)
                                :].strip("\n").split("\t")
        return EventIDOnly(tokens[1])
    else:
        tokens = line[line.find(SIEVE_BEFORE_EVENT_MARK)
                                :].strip("\n").split("\t")
        return EventIDOnly(tokens[1])


def parse_side_effect_id_only(line):
    assert SIEVE_AFTER_SIDE_EFFECT_MARK in line or SIEVE_BEFORE_SIDE_EFFECT_MARK in line
    if SIEVE_AFTER_SIDE_EFFECT_MARK in line:
        tokens = line[line.find(SIEVE_AFTER_SIDE_EFFECT_MARK):].strip(
            "\n").split("\t")
        return SideEffectIDOnly(tokens[1])
    else:
        tokens = line[line.find(SIEVE_BEFORE_SIDE_EFFECT_MARK):].strip(
            "\n").split("\t")
        return SideEffectIDOnly(tokens[1])


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


class CausalityVertex:
    vertex_cnt = 0

    def __init__(self, content):
        self.id = CausalityVertex.vertex_cnt
        CausalityVertex.vertex_cnt += 1
        self.content = content
        self.outgoing_edges = {}

    def get_id(self):
        return self.id

    def get_content(self):
        return self.content

    def is_event(self):
        return isinstance(self.content, Event)

    def is_side_effect(self):
        return isinstance(self.content, SideEffect)


class CausalityEdge:
    edge_cnt = 0

    def __init__(self, source: CausalityVertex, sink: CausalityVertex, type: str):
        self.id = CausalityEdge.edge_cnt
        CausalityEdge.edge_cnt += 1
        self.source = source
        self.sink = sink
        self.type = type

    def get_source(self):
        return self.source

    def get_sink(self):
        return self.sink


class CausalityGraph:
    def __init__(self):
        self.vertices = {}
        self.edges = {}

    def sanity_check(self):
        for edge in self.edges.values():
            source = edge.get_source()
            sink = edge.get_sink()
            assert isinstance(source, CausalityVertex)
            assert isinstance(sink, CausalityVertex)
            assert source.get_id() != sink.get_id()
            assert source.get_id() in self.vertices
            assert sink.get_id() in self.vertices
            assert (source.is_event() and sink.is_side_effect()) or (
                sink.is_event() and source.is_side_effect())

    def add_vertex(self, vertex: CausalityVertex):
        if vertex.id not in self.vertices:
            self.vertices[vertex.id] = vertex

    def add_edge(self, edge: CausalityEdge):
        if edge.id not in self.edges:
            self.edges[edge.id] = edge

    def get_vertices(self) -> List[CausalityVertex]:
        return list(self.vertices.values())

    def get_event_vertices(self) -> List[CausalityVertex]:
        vertices = self.get_vertices()
        event_vertices = []
        for vertex in vertices:
            if vertex.is_event():
                event_vertices.append(vertex)
        return event_vertices

    def get_side_effect_vertices(self) -> List[CausalityVertex]:
        vertices = self.get_vertices()
        side_effect_vertices = []
        for vertex in vertices:
            if vertex.is_side_effect():
                side_effect_vertices.append(vertex)
        return side_effect_vertices

    def get_edges(self) -> List[CausalityEdge]:
        return list(self.edges.values())

    def get_event_effect_edge(self) -> List[CausalityEdge]:
        edges = self.get_edges()
        event_effect_edges = []
        for edge in edges:
            if edge.get_source().is_event() and edge.get_sink().is_side_effect():
                event_effect_edges.append(edge)
        return event_effect_edges

    def connect_vertex(self, source: CausalityVertex, sink: CausalityVertex, type: str):
        if source.id not in self.vertices:
            self.vertices[source.id] = source
        if sink.id not in self.vertices:
            self.vertices[sink.id] = sink
        edge = CausalityEdge(source, sink, type)
        self.edges[edge.id] = edge
