import json
from typing import List, Dict, Optional, Union, Set
import sieve_config

WRITE_READ_FILTER_FLAG = True
ERROR_MSG_FILTER_FLAG = True

# flags for time travel only
DELETE_ONLY_FILTER_FLAG = True
DELETE_THEN_RECREATE_FLAG = True

# flags for obs gap only
CANCELLABLE_FLAG = True

# flags for atom vio only
READ_BEFORE_EFFECT_FLAG = True

FILTERED_ERROR_TYPE = ["NotFound", "Conflict"]
ALLOWED_ERROR_TYPE = ["NoError"]

SIEVE_BEFORE_EVENT_MARK = "[SIEVE-BEFORE-EVENT]"
SIEVE_AFTER_EVENT_MARK = "[SIEVE-AFTER-EVENT]"
SIEVE_BEFORE_SIDE_EFFECT_MARK = "[SIEVE-BEFORE-SIDE-EFFECT]"
SIEVE_AFTER_SIDE_EFFECT_MARK = "[SIEVE-AFTER-SIDE-EFFECT]"
SIEVE_AFTER_READ_MARK = "[SIEVE-AFTER-READ]"
SIEVE_BEFORE_RECONCILE_MARK = "[SIEVE-BEFORE-RECONCILE]"
SIEVE_AFTER_RECONCILE_MARK = "[SIEVE-AFTER-RECONCILE]"

INTRA_THREAD_EDGE = "INTRA-THREAD"
INTER_THREAD_EDGE = "INTER-THREADS"


class EventTypes:
    ADDED = "Added"
    UPDATED = "Updated"
    DELETED = "Deleted"


class SideEffectTypes:
    CREATE = "Create"
    UPDATE = "Update"
    DELETE = "Delete"


def consistent_type(event_type: str, side_effect_type: str):
    both_create = (
        event_type == EventTypes.ADDED and side_effect_type == SideEffectTypes.CREATE
    )
    both_update = (
        event_type == EventTypes.UPDATED and side_effect_type == SideEffectTypes.UPDATE
    )
    both_delete = (
        event_type == EventTypes.DELETED and side_effect_type == SideEffectTypes.DELETE
    )
    return both_create or both_update or both_delete


def extract_namespace_name(obj: Dict):
    assert "metadata" in obj, "missing metadata in: " + str(obj)
    # TODO(Wenqing): Sometimes metadata doesn't carry namespace field, may dig into that later
    obj_name = obj["metadata"]["name"]
    obj_namespace = (
        obj["metadata"]["namespace"]
        if "namespace" in obj["metadata"]
        else sieve_config.config["namespace"]
    )
    return obj_namespace, obj_name


def generate_key(resource_type: str, namespace: str, name: str):
    return "/".join([resource_type, namespace, name])


class Event:
    def __init__(self, id: str, etype: str, rtype: str, obj_str: str):
        self.__id = int(id)
        self.__etype = etype
        self.__rtype = rtype
        self.__obj_str = obj_str
        self.__obj_map = json.loads(obj_str)
        self.__namespace, self.__name = extract_namespace_name(self.obj_map)
        self.__start_timestamp = -1
        self.__end_timestamp = -1
        self.__key = generate_key(self.rtype, self.namespace, self.name)
        self.__slim_prev_obj_map = None
        self.__slim_cur_obj_map = None
        self.__prev_etype = None
        self.__cancelled_by = set()

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

    @property
    def slim_prev_obj_map(self):
        return self.__slim_prev_obj_map

    @property
    def slim_cur_obj_map(self):
        return self.__slim_cur_obj_map

    @property
    def prev_etype(self):
        return self.__prev_etype

    @property
    def cancelled_by(self):
        return self.__cancelled_by

    @start_timestamp.setter
    def start_timestamp(self, start_timestamp: int):
        self.__start_timestamp = start_timestamp

    @end_timestamp.setter
    def end_timestamp(self, end_timestamp: int):
        self.__end_timestamp = end_timestamp

    @slim_prev_obj_map.setter
    def slim_prev_obj_map(self, slim_prev_obj_map: Dict):
        self.__slim_prev_obj_map = slim_prev_obj_map

    @slim_cur_obj_map.setter
    def slim_cur_obj_map(self, slim_cur_obj_map: Dict):
        self.__slim_cur_obj_map = slim_cur_obj_map

    @prev_etype.setter
    def prev_etype(self, prev_etype: str):
        self.__prev_etype = prev_etype

    @cancelled_by.setter
    def cancelled_by(self, cancelled_by: Set):
        self.__cancelled_by = cancelled_by


class SideEffect:
    def __init__(self, id: str, etype: str, rtype: str, error: str, obj_str: str):
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
        self.__key = generate_key(self.rtype, self.namespace, self.name)

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
    def start_timestamp(self, start_timestamp: int):
        self.__start_timestamp = start_timestamp

    @end_timestamp.setter
    def end_timestamp(self, end_timestamp: int):
        self.__end_timestamp = end_timestamp

    @read_types.setter
    def read_types(self, read_types: Set[str]):
        self.__read_types = read_types

    @read_keys.setter
    def read_keys(self, read_keys: Set[str]):
        self.__read_keys = read_keys

    def set_range(self, start_timestamp: int, end_timestamp: int):
        assert start_timestamp < end_timestamp
        self.__range_start_timestamp = start_timestamp
        self.__range_end_timestamp = end_timestamp


def range_overlap(side_effect: SideEffect, event: Event):
    # This is the key method to generate the (event, side_effect) pairs
    assert side_effect.range_end_timestamp != -1
    assert event.start_timestamp != -1
    assert event.end_timestamp != -1
    assert side_effect.range_start_timestamp < side_effect.range_end_timestamp
    assert side_effect.start_timestamp < side_effect.end_timestamp
    assert side_effect.end_timestamp == side_effect.range_end_timestamp
    assert event.start_timestamp < event.end_timestamp
    return (
        side_effect.range_start_timestamp < event.end_timestamp
        and side_effect.start_timestamp > event.start_timestamp
    )


def interest_overlap(side_effect: SideEffect, event: Event):
    return event.key in side_effect.read_keys or event.rtype in side_effect.read_types


class CacheRead:
    def __init__(
        self,
        etype: str,
        rtype: str,
        namespace: str,
        name: str,
        error: str,
        obj_str: str,
    ):
        self.__etype = etype
        self.__rtype = rtype
        self.__error = error
        self.__obj_list = []
        self.__key_set = set()
        if etype == "Get":
            self.obj_list.append(json.loads(obj_str))
            self.key_set.add(generate_key(self.rtype, namespace, name))
        else:
            self.obj_list.extend(json.loads(obj_str)["items"])
            for obj in self.obj_list:
                key = generate_key(
                    self.rtype, obj["metadata"]["namespace"], obj["metadata"]["name"]
                )
                self.key_set.add(key)

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
    def key_set(self):
        return self.__key_set

    @property
    def obj_list(self):
        return self.__obj_list


class EventIDOnly:
    def __init__(self, id: str):
        self.__id = int(id)

    @property
    def id(self):
        return self.__id


class SideEffectIDOnly:
    def __init__(self, id: str):
        self.__id = int(id)

    @property
    def id(self):
        return self.__id


class Reconcile:
    def __init__(self, controller_name: str, round_id: str):
        self.__controller_name = controller_name
        self.__round_id = round_id

    @property
    def controller_name(self):
        return self.__controller_name

    @property
    def round_id(self):
        return self.__round_id


def parse_event(line: str) -> Event:
    assert SIEVE_BEFORE_EVENT_MARK in line
    tokens = line[line.find(SIEVE_BEFORE_EVENT_MARK) :].strip("\n").split("\t")
    return Event(tokens[1], tokens[2], tokens[3], tokens[4])


def parse_side_effect(line: str) -> SideEffect:
    assert SIEVE_AFTER_SIDE_EFFECT_MARK in line
    tokens = line[line.find(SIEVE_AFTER_SIDE_EFFECT_MARK) :].strip("\n").split("\t")
    return SideEffect(tokens[1], tokens[2], tokens[3], tokens[4], tokens[5])


def parse_cache_read(line: str) -> CacheRead:
    assert SIEVE_AFTER_READ_MARK in line
    tokens = line[line.find(SIEVE_AFTER_READ_MARK) :].strip("\n").split("\t")
    if tokens[1] == "Get":
        return CacheRead(
            tokens[1], tokens[2], tokens[3], tokens[4], tokens[5], tokens[6]
        )
    else:
        # When using List, the resource type is like xxxlist so we need to trim the last four characters here
        assert tokens[2].endswith("list")
        return CacheRead(tokens[1], tokens[2][:-4], "", "", tokens[3], tokens[4])


def parse_event_id_only(line: str) -> EventIDOnly:
    assert SIEVE_AFTER_EVENT_MARK in line or SIEVE_BEFORE_EVENT_MARK in line
    if SIEVE_AFTER_EVENT_MARK in line:
        tokens = line[line.find(SIEVE_AFTER_EVENT_MARK) :].strip("\n").split("\t")
        return EventIDOnly(tokens[1])
    else:
        tokens = line[line.find(SIEVE_BEFORE_EVENT_MARK) :].strip("\n").split("\t")
        return EventIDOnly(tokens[1])


def parse_side_effect_id_only(line: str) -> SideEffectIDOnly:
    assert SIEVE_AFTER_SIDE_EFFECT_MARK in line or SIEVE_BEFORE_SIDE_EFFECT_MARK in line
    if SIEVE_AFTER_SIDE_EFFECT_MARK in line:
        tokens = line[line.find(SIEVE_AFTER_SIDE_EFFECT_MARK) :].strip("\n").split("\t")
        return SideEffectIDOnly(tokens[1])
    else:
        tokens = (
            line[line.find(SIEVE_BEFORE_SIDE_EFFECT_MARK) :].strip("\n").split("\t")
        )
        return SideEffectIDOnly(tokens[1])


def parse_reconcile(line: str) -> Reconcile:
    assert SIEVE_BEFORE_RECONCILE_MARK in line or SIEVE_AFTER_RECONCILE_MARK in line
    if SIEVE_BEFORE_RECONCILE_MARK in line:
        tokens = line[line.find(SIEVE_BEFORE_RECONCILE_MARK) :].strip("\n").split("\t")
        return Reconcile(tokens[1], tokens[2])
    else:
        tokens = line[line.find(SIEVE_AFTER_RECONCILE_MARK) :].strip("\n").split("\t")
        return Reconcile(tokens[1], tokens[2])


class CausalityVertex:
    def __init__(self, gid: int, content: Union[Event, SideEffect]):
        self.__gid = gid
        self.__content = content
        self.__out_edges = []

    @property
    def gid(self):
        return self.__gid

    @property
    def content(self):
        return self.__content

    @property
    def out_edges(self):
        return self.__out_edges

    def add_out_edge(self, edge):
        self.out_edges.append(edge)

    def is_event(self) -> bool:
        return isinstance(self.content, Event)

    def is_side_effect(self) -> bool:
        return isinstance(self.content, SideEffect)


class CausalityEdge:
    def __init__(self, source: CausalityVertex, sink: CausalityVertex, type: str):
        self.__source = source
        self.__sink = sink
        self.__type = type

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
        self.__vertex_cnt = 0
        self.__event_vertices = []
        self.__side_effect_vertices = []
        self.__event_key_to_event_vertices = {}
        self.__event_id_to_event_vertices = {}
        self.__event_side_effect_edges = []
        self.__side_effect_event_edges = []

    @property
    def event_vertices(self) -> List[CausalityVertex]:
        return self.__event_vertices

    @property
    def side_effect_vertices(self) -> List[CausalityVertex]:
        return self.__side_effect_vertices

    @property
    def event_key_to_event_vertices(self) -> Dict[str, List[CausalityVertex]]:
        return self.__event_key_to_event_vertices

    @property
    def event_id_to_event_vertices(self) -> Dict[int, List[CausalityVertex]]:
        return self.__event_id_to_event_vertices

    @property
    def event_side_effect_edges(self) -> List[CausalityEdge]:
        return self.__event_side_effect_edges

    @property
    def side_effect_event_edges(self) -> List[CausalityEdge]:
        return self.__side_effect_event_edges

    def get_event_with_id(self, event_id) -> Optional[CausalityVertex]:
        if event_id in self.event_id_to_event_vertices:
            return self.event_id_to_event_vertices[event_id]
        else:
            return None

    def get_prev_event_with_key(self, key, cur_event_id) -> Optional[CausalityVertex]:
        for i in range(len(self.event_key_to_event_vertices[key])):
            event_vertex = self.event_key_to_event_vertices[key][i]
            if event_vertex.content.id == cur_event_id:
                if i == 0:
                    return None
                else:
                    return self.event_key_to_event_vertices[key][i - 1]

    def sanity_check(self):
        # Be careful!!! The event_id and side_effect_id are only used to differentiate events/side effects
        # the id value does not indicate which event/side effect happens earlier/later
        # TODO(xudong): maybe we should also make the id consistent with start_timestamp?
        print("%d event vertices" % len(self.event_vertices))
        print("%d side_effect vertices" % len(self.side_effect_vertices))
        print("%d edges from event to side_effect" % len(self.event_side_effect_edges))
        print("%d edges from side_effect to event" % len(self.side_effect_event_edges))
        for i in range(len(self.event_vertices)):
            if i > 0:
                assert self.event_vertices[i].gid == self.event_vertices[i - 1].gid + 1
                assert (
                    self.event_vertices[i].content.start_timestamp
                    > self.event_vertices[i - 1].content.start_timestamp
                )
            assert self.event_vertices[i].is_event
            for edge in self.event_vertices[i].out_edges:
                assert self.event_vertices[i].gid == edge.source.gid
        for i in range(len(self.side_effect_vertices)):
            if i > 0:
                assert (
                    self.side_effect_vertices[i].gid
                    == self.side_effect_vertices[i - 1].gid + 1
                )
                assert (
                    self.side_effect_vertices[i].content.start_timestamp
                    > self.side_effect_vertices[i - 1].content.start_timestamp
                )
            assert self.side_effect_vertices[i].is_side_effect
            for edge in self.side_effect_vertices[i].out_edges:
                assert self.side_effect_vertices[i].gid == edge.source.gid
        for edge in self.event_side_effect_edges:
            assert isinstance(edge.source, CausalityVertex)
            assert isinstance(edge.sink, CausalityVertex)
            assert edge.source.is_event() and edge.sink.is_side_effect()
            assert (
                edge.source.content.start_timestamp < edge.sink.content.start_timestamp
            )
        for edge in self.side_effect_event_edges:
            assert isinstance(edge.source, CausalityVertex)
            assert isinstance(edge.sink, CausalityVertex)
            assert edge.sink.is_event() and edge.source.is_side_effect()
            assert (
                edge.source.content.start_timestamp < edge.sink.content.start_timestamp
            )

    def add_sorted_events(self, event_list: List[Event]):
        for i in range(len(event_list)):
            event = event_list[i]
            event_vertex = CausalityVertex(self.__vertex_cnt, event)
            self.__vertex_cnt += 1
            self.event_vertices.append(event_vertex)
            if event_vertex.content.key not in self.event_key_to_event_vertices:
                self.event_key_to_event_vertices[event_vertex.content.key] = []
            self.event_key_to_event_vertices[event_vertex.content.key].append(
                event_vertex
            )
            assert event_vertex.content.id not in self.event_id_to_event_vertices
            self.event_id_to_event_vertices[event_vertex.content.id] = event_vertex

    def add_sorted_side_effects(self, side_effect_list: List[SideEffect]):
        for i in range(len(side_effect_list)):
            side_effect = side_effect_list[i]
            side_effect_vertex = CausalityVertex(self.__vertex_cnt, side_effect)
            self.__vertex_cnt += 1
            self.side_effect_vertices.append(side_effect_vertex)

    def connect_event_to_side_effect(
        self, event_vertex: CausalityVertex, side_effect_vertex: CausalityVertex
    ):
        assert event_vertex.is_event()
        assert side_effect_vertex.is_side_effect()
        assert (
            event_vertex.content.start_timestamp
            < side_effect_vertex.content.start_timestamp
        )
        edge = CausalityEdge(event_vertex, side_effect_vertex, INTER_THREAD_EDGE)
        event_vertex.add_out_edge(edge)
        self.event_side_effect_edges.append(edge)

    def connect_side_effect_to_event(
        self, side_effect_vertex: CausalityVertex, event_vertex: CausalityVertex
    ):
        assert event_vertex.is_event()
        assert side_effect_vertex.is_side_effect()
        assert (
            side_effect_vertex.content.start_timestamp
            < event_vertex.content.start_timestamp
        )
        edge = CausalityEdge(side_effect_vertex, event_vertex, INTER_THREAD_EDGE)
        side_effect_vertex.add_out_edge(edge)
        self.side_effect_event_edges.append(edge)


def causality_vertice_connected(source: CausalityVertex, sink: CausalityVertex):
    # there should be no cycles in the casuality graph
    queue = []
    visited = set()
    queue.append(source)
    visited.add(source.gid)
    if source.gid == sink.gid:
        return True
    while len(queue) != 0:
        cur = queue.pop(0)
        for edge in cur.out_edges:
            assert cur.gid == edge.source.gid
            assert (
                edge.source.content.start_timestamp < edge.sink.content.start_timestamp
            )
            if edge.sink.gid == sink.gid:
                return True
            else:
                if edge.sink.gid not in visited:
                    visited.add(edge.sink.gid)
                    queue.append(edge.sink)
    return False
