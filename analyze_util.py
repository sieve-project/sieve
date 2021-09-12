import json
from typing import List, Union
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
        self.__id = int(id)
        self.__etype = etype
        self.__rtype = rtype
        self.__obj_str = obj_str
        self.__obj_map = json.loads(obj_str)
        self.__namespace, self.__name = extract_namespace_name(self.obj_map)
        self.__start_timestamp = -1
        self.__end_timestamp = -1
        self.__key = self.rtype + "/" + self.namespace + "/" + self.name

    @property
    def id(self):
        return self.__id

    @property
    def etype(self):
        return self.__etype

    @property
    def rtype(self):
        return self.__rtype

    @property
    def obj_str(self):
        return self.__obj_str

    @property
    def obj_map(self):
        return self.__obj_map

    @property
    def namespace(self):
        return self.__namespace

    @property
    def name(self):
        return self.__name

    @property
    def start_timestamp(self):
        return self.__start_timestamp

    @property
    def end_timestamp(self):
        return self.__end_timestamp

    @property
    def key(self):
        return self.__key

    @start_timestamp.setter
    def start_timestamp(self, start_timestamp):
        self.__start_timestamp = start_timestamp

    @end_timestamp.setter
    def end_timestamp(self, end_timestamp):
        self.__end_timestamp = end_timestamp


class SideEffect:
    def __init__(self, id, etype, rtype, error, obj_str):
        self.__id = int(id)
        self.__etype = etype
        self.__rtype = rtype
        self.__error = error
        self.__obj_str = obj_str
        self.__obj_map = json.loads(obj_str)
        self.__namespace, self.__name = extract_namespace_name(self.obj_map)
        self.__start_timestamp = -1
        self.__end_timestamp = -1
        self.__range_start_timestamp = -1
        self.__range_end_timestamp = -1
        self.__read_types = set()
        self.__read_keys = set()
        self.__owner_controllers = set()
        self.__key = self.rtype + "/" + self.namespace + "/" + self.name

    @property
    def id(self):
        return self.__id

    @property
    def etype(self):
        return self.__etype

    @property
    def rtype(self):
        return self.__rtype

    @property
    def error(self):
        return self.__error

    @property
    def obj_str(self):
        return self.__obj_str

    @property
    def obj_map(self):
        return self.__obj_map

    @property
    def namespace(self):
        return self.__namespace

    @property
    def name(self):
        return self.__name

    @property
    def read_types(self):
        return self.__read_types

    @property
    def read_keys(self):
        return self.__read_keys

    @property
    def start_timestamp(self):
        return self.__start_timestamp

    @property
    def end_timestamp(self):
        return self.__end_timestamp

    @property
    def range_start_timestamp(self):
        return self.__range_start_timestamp

    @property
    def range_end_timestamp(self):
        return self.__range_end_timestamp

    @property
    def owner_controllers(self):
        return self.__owner_controllers

    @property
    def key(self):
        return self.__key

    @start_timestamp.setter
    def start_timestamp(self, start_timestamp):
        self.__start_timestamp = start_timestamp

    @end_timestamp.setter
    def end_timestamp(self, end_timestamp):
        self.__end_timestamp = end_timestamp

    @read_types.setter
    def read_types(self, read_types):
        self.__read_types = read_types

    @read_keys.setter
    def read_keys(self, read_keys):
        self.__read_keys = read_keys

    def set_range(self, start_timestamp, end_timestamp):
        assert start_timestamp < end_timestamp
        self.__range_start_timestamp = start_timestamp
        self.__range_end_timestamp = end_timestamp

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
        self.__etype = etype
        self.__rtype = rtype
        self.__namespace = namespace
        self.__name = name
        self.__error = error
        self.__key = self.rtype + "/" + self.namespace + "/" + self.name

    @property
    def etype(self):
        return self.__etype

    @property
    def rtype(self):
        return self.__rtype

    @property
    def error(self):
        return self.__error

    @property
    def key(self):
        return self.__key

    @property
    def namespace(self):
        return self.__namespace

    @property
    def name(self):
        return self.__name


class EventIDOnly:
    def __init__(self, id):
        self.__id = int(id)

    @property
    def id(self):
        return self.__id


class SideEffectIDOnly:
    def __init__(self, id):
        self.__id = int(id)

    @property
    def id(self):
        return self.__id


class Reconcile:
    def __init__(self, controller_name, round_id):
        self.__controller_name = controller_name
        self.__round_id = round_id

    @property
    def controller_name(self):
        return self.__controller_name

    @property
    def round_id(self):
        return self.__round_id


class EventsDataStructure:
    def __init__(self, event_list, event_key_map, event_id_map):
        self.event_list = event_list
        self.event_key_map = event_key_map
        self.event_id_map = event_id_map


class SideEffectsDataStructure:
    def __init__(self, side_effect_list, side_effect_id_map):
        self.side_effect_list = side_effect_list
        self.side_effect_id_map = side_effect_id_map


def parse_event(line: str) -> Event:
    assert SIEVE_BEFORE_EVENT_MARK in line
    tokens = line[line.find(SIEVE_BEFORE_EVENT_MARK):].strip("\n").split("\t")
    return Event(tokens[1], tokens[2], tokens[3], tokens[4])


def parse_side_effect(line: str) -> SideEffect:
    assert SIEVE_AFTER_SIDE_EFFECT_MARK in line
    tokens = line[line.find(SIEVE_AFTER_SIDE_EFFECT_MARK)                  :].strip("\n").split("\t")
    return SideEffect(tokens[1], tokens[2], tokens[3], tokens[4], tokens[5])


def parse_cache_read(line: str) -> CacheRead:
    assert SIEVE_AFTER_READ_MARK in line
    tokens = line[line.find(SIEVE_AFTER_READ_MARK):].strip("\n").split("\t")
    if tokens[1] == "Get":
        return CacheRead(tokens[1], tokens[2], tokens[3], tokens[4], tokens[5])
    else:
        # When using List, the resource type is like xxxlist so we need to trim the last four characters here
        assert tokens[2].endswith("list")
        return CacheRead(tokens[1], tokens[2][:-4], "", "", tokens[3])


def parse_event_id_only(line: str) -> EventIDOnly:
    assert SIEVE_AFTER_EVENT_MARK in line or SIEVE_BEFORE_EVENT_MARK in line
    if SIEVE_AFTER_EVENT_MARK in line:
        tokens = line[line.find(SIEVE_AFTER_EVENT_MARK)                      :].strip("\n").split("\t")
        return EventIDOnly(tokens[1])
    else:
        tokens = line[line.find(SIEVE_BEFORE_EVENT_MARK)                      :].strip("\n").split("\t")
        return EventIDOnly(tokens[1])


def parse_side_effect_id_only(line: str) -> SideEffectIDOnly:
    assert SIEVE_AFTER_SIDE_EFFECT_MARK in line or SIEVE_BEFORE_SIDE_EFFECT_MARK in line
    if SIEVE_AFTER_SIDE_EFFECT_MARK in line:
        tokens = line[line.find(SIEVE_AFTER_SIDE_EFFECT_MARK):].strip(
            "\n").split("\t")
        return SideEffectIDOnly(tokens[1])
    else:
        tokens = line[line.find(SIEVE_BEFORE_SIDE_EFFECT_MARK):].strip(
            "\n").split("\t")
        return SideEffectIDOnly(tokens[1])


def parse_reconcile(line: str) -> Reconcile:
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

    def __init__(self, content: Union[Event, SideEffect]):
        self.__id = CausalityVertex.vertex_cnt
        CausalityVertex.vertex_cnt += 1
        self.__content = content

    @property
    def id(self):
        return self.__id

    @property
    def content(self):
        return self.__content

    def is_event(self) -> bool:
        return isinstance(self.content, Event)

    def is_side_effect(self) -> bool:
        return isinstance(self.content, SideEffect)


class CausalityEdge:
    edge_cnt = 0

    def __init__(self, source: CausalityVertex, sink: CausalityVertex, type: str):
        self.__id = CausalityEdge.edge_cnt
        CausalityEdge.edge_cnt += 1
        self.__source = source
        self.__sink = sink
        self.__type = type

    @property
    def id(self):
        return self.__id

    @property
    def source(self):
        return self.__source

    @property
    def sink(self):
        return self.__sink

    @property
    def type(self):
        return self.__type


class CausalityGraph:
    def __init__(self):
        self.__vertices = {}
        self.__edges = {}

    @property
    def vertices(self):
        return self.__vertices

    @property
    def edges(self):
        return self.__edges

    def sanity_check(self):
        for edge in self.edges.values():
            assert isinstance(edge.source, CausalityVertex)
            assert isinstance(edge.sink, CausalityVertex)
            assert edge.source.id != edge.sink.id
            assert edge.source.id in self.vertices
            assert edge.sink.id in self.vertices
            assert (edge.source.is_event() and edge.sink.is_side_effect()) or (
                edge.sink.is_event() and edge.source.is_side_effect())

    def add_vertex(self, vertex: CausalityVertex):
        if vertex.id not in self.__vertices:
            self.__vertices[vertex.id] = vertex

    def add_edge(self, edge: CausalityEdge):
        if edge.id not in self.__edges:
            self.__edges[edge.id] = edge

    def get_vertex_list(self) -> List[CausalityVertex]:
        return list(self.vertices.values())

    def get_event_vertex_list(self) -> List[CausalityVertex]:
        vertices = self.get_vertex_list()
        event_vertices = []
        for vertex in vertices:
            if vertex.is_event():
                event_vertices.append(vertex)
        return event_vertices

    def get_side_effect_vertex_list(self) -> List[CausalityVertex]:
        vertices = self.get_vertex_list()
        side_effect_vertices = []
        for vertex in vertices:
            if vertex.is_side_effect():
                side_effect_vertices.append(vertex)
        return side_effect_vertices

    def get_edge_list(self) -> List[CausalityEdge]:
        return list(self.edges.values())

    def get_event_effect_edge_list(self) -> List[CausalityEdge]:
        edges = self.get_edge_list()
        event_effect_edges = []
        for edge in edges:
            if edge.source.is_event() and edge.sink.is_side_effect():
                event_effect_edges.append(edge)
        return event_effect_edges
