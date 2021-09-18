import json
from typing import List, Dict, Optional, Union, Set
import sieve_config

HEAR_READ_FILTER_FLAG = True
ERROR_MSG_FILTER_FLAG = True

# flags for time travel only
DELETE_ONLY_FILTER_FLAG = True
DELETE_THEN_RECREATE_FLAG = True

# flags for obs gap only
CANCELLABLE_FLAG = True

# flags for atom vio only
READ_BEFORE_WRITE_FLAG = True

FILTERED_ERROR_TYPE = ["NotFound", "Conflict"]
ALLOWED_ERROR_TYPE = ["NoError"]

SIEVE_BEFORE_HEAR_MARK = "[SIEVE-BEFORE-EVENT]"
SIEVE_AFTER_HEAR_MARK = "[SIEVE-AFTER-EVENT]"
SIEVE_BEFORE_WRITE_MARK = "[SIEVE-BEFORE-SIDE-EFFECT]"
SIEVE_AFTER_WRITE_MARK = "[SIEVE-AFTER-SIDE-EFFECT]"
SIEVE_AFTER_READ_MARK = "[SIEVE-AFTER-READ]"
SIEVE_BEFORE_RECONCILE_MARK = "[SIEVE-BEFORE-RECONCILE]"
SIEVE_AFTER_RECONCILE_MARK = "[SIEVE-AFTER-RECONCILE]"

HEAR_WRITE_EDGE = "HEAR-WRITE"
WRITE_HEAR_EDGE = "WRITE-HEAR"


class OperatorHearTypes:
    ADDED = "Added"
    UPDATED = "Updated"
    DELETED = "Deleted"


class OperatorWriteTypes:
    CREATE = "Create"
    UPDATE = "Update"
    DELETE = "Delete"


def consistent_type(operator_hear_type: str, operator_write_type: str):
    both_create = (
        operator_hear_type == OperatorHearTypes.ADDED
        and operator_write_type == OperatorWriteTypes.CREATE
    )
    both_update = (
        operator_hear_type == OperatorHearTypes.UPDATED
        and operator_write_type == OperatorWriteTypes.UPDATE
    )
    both_delete = (
        operator_hear_type == OperatorHearTypes.DELETED
        and operator_write_type == OperatorWriteTypes.DELETE
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


class OperatorHear:
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


class OperatorWrite:
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
        self.__slim_prev_obj_map = None
        self.__slim_cur_obj_map = None

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

    @property
    def slim_prev_obj_map(self):
        return self.__slim_prev_obj_map

    @property
    def slim_cur_obj_map(self):
        return self.__slim_cur_obj_map

    @property
    def prev_etype(self):
        return self.__prev_etype

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

    @slim_prev_obj_map.setter
    def slim_prev_obj_map(self, slim_prev_obj_map: Dict):
        self.__slim_prev_obj_map = slim_prev_obj_map

    @slim_cur_obj_map.setter
    def slim_cur_obj_map(self, slim_cur_obj_map: Dict):
        self.__slim_cur_obj_map = slim_cur_obj_map

    @prev_etype.setter
    def prev_etype(self, prev_etype: str):
        self.__prev_etype = prev_etype

    def set_range(self, start_timestamp: int, end_timestamp: int):
        assert start_timestamp < end_timestamp
        self.__range_start_timestamp = start_timestamp
        self.__range_end_timestamp = end_timestamp


def range_overlap(operator_write: OperatorWrite, operator_hear: OperatorHear):
    # This is the key method to generate the (operator_hear, operator_write) pairs
    assert operator_write.range_end_timestamp != -1
    assert operator_hear.start_timestamp != -1
    assert operator_hear.end_timestamp != -1
    assert operator_write.range_start_timestamp < operator_write.range_end_timestamp
    assert operator_write.start_timestamp < operator_write.end_timestamp
    assert operator_write.end_timestamp == operator_write.range_end_timestamp
    assert operator_hear.start_timestamp < operator_hear.end_timestamp
    return (
        operator_write.range_start_timestamp < operator_hear.end_timestamp
        and operator_write.start_timestamp > operator_hear.start_timestamp
    )


def interest_overlap(operator_write: OperatorWrite, operator_hear: OperatorHear):
    return (
        operator_hear.key in operator_write.read_keys
        or operator_hear.rtype in operator_write.read_types
    )


class OperatorRead:
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
        self.__key_to_obj = {}
        self.__key_set = set()
        self.__end_timestamp = -1
        if etype == "Get":
            key = generate_key(self.rtype, namespace, name)
            self.key_set.add(key)
            self.key_to_obj[key] = json.loads(obj_str)
        else:
            objs = json.loads(obj_str)["items"]
            for obj in objs:
                key = generate_key(
                    self.rtype, obj["metadata"]["namespace"], obj["metadata"]["name"]
                )
                assert key not in self.key_set
                assert key not in self.key_to_obj
                self.key_set.add(key)
                self.key_to_obj[key] = obj

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
    def key_to_obj(self):
        return self.__key_to_obj

    @property
    def end_timestamp(self):
        return self.__end_timestamp

    @end_timestamp.setter
    def end_timestamp(self, end_timestamp: int):
        self.__end_timestamp = end_timestamp


class OperatorHearIDOnly:
    def __init__(self, id: str):
        self.__id = int(id)

    @property
    def id(self):
        return self.__id


class OperatorWriteIDOnly:
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


def parse_operator_hear(line: str) -> OperatorHear:
    assert SIEVE_BEFORE_HEAR_MARK in line
    tokens = line[line.find(SIEVE_BEFORE_HEAR_MARK) :].strip("\n").split("\t")
    return OperatorHear(tokens[1], tokens[2], tokens[3], tokens[4])


def parse_operator_write(line: str) -> OperatorWrite:
    assert SIEVE_AFTER_WRITE_MARK in line
    tokens = line[line.find(SIEVE_AFTER_WRITE_MARK) :].strip("\n").split("\t")
    return OperatorWrite(tokens[1], tokens[2], tokens[3], tokens[4], tokens[5])


def parse_operator_read(line: str) -> OperatorRead:
    assert SIEVE_AFTER_READ_MARK in line
    tokens = line[line.find(SIEVE_AFTER_READ_MARK) :].strip("\n").split("\t")
    if tokens[1] == "Get":
        return OperatorRead(
            tokens[1], tokens[2], tokens[3], tokens[4], tokens[5], tokens[6]
        )
    else:
        # When using List, the resource type is like xxxlist so we need to trim the last four characters here
        assert tokens[2].endswith("list")
        return OperatorRead(tokens[1], tokens[2][:-4], "", "", tokens[3], tokens[4])


def parse_operator_hear_id_only(line: str) -> OperatorHearIDOnly:
    assert SIEVE_AFTER_HEAR_MARK in line or SIEVE_BEFORE_HEAR_MARK in line
    if SIEVE_AFTER_HEAR_MARK in line:
        tokens = line[line.find(SIEVE_AFTER_HEAR_MARK) :].strip("\n").split("\t")
        return OperatorHearIDOnly(tokens[1])
    else:
        tokens = line[line.find(SIEVE_BEFORE_HEAR_MARK) :].strip("\n").split("\t")
        return OperatorHearIDOnly(tokens[1])


def parse_operator_write_id_only(line: str) -> OperatorWriteIDOnly:
    assert SIEVE_AFTER_WRITE_MARK in line or SIEVE_BEFORE_WRITE_MARK in line
    if SIEVE_AFTER_WRITE_MARK in line:
        tokens = line[line.find(SIEVE_AFTER_WRITE_MARK) :].strip("\n").split("\t")
        return OperatorWriteIDOnly(tokens[1])
    else:
        tokens = line[line.find(SIEVE_BEFORE_WRITE_MARK) :].strip("\n").split("\t")
        return OperatorWriteIDOnly(tokens[1])


def parse_reconcile(line: str) -> Reconcile:
    assert SIEVE_BEFORE_RECONCILE_MARK in line or SIEVE_AFTER_RECONCILE_MARK in line
    if SIEVE_BEFORE_RECONCILE_MARK in line:
        tokens = line[line.find(SIEVE_BEFORE_RECONCILE_MARK) :].strip("\n").split("\t")
        return Reconcile(tokens[1], tokens[2])
    else:
        tokens = line[line.find(SIEVE_AFTER_RECONCILE_MARK) :].strip("\n").split("\t")
        return Reconcile(tokens[1], tokens[2])


class CausalityVertex:
    def __init__(self, gid: int, content: Union[OperatorHear, OperatorWrite]):
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

    def is_operator_hear(self) -> bool:
        return isinstance(self.content, OperatorHear)

    def is_operator_write(self) -> bool:
        return isinstance(self.content, OperatorWrite)


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
        self.__operator_hear_vertices = []
        self.__operator_write_vertices = []
        self.__operator_hear_key_to_operator_hear_vertices = {}
        self.__operator_hear_id_to_operator_hear_vertices = {}
        self.__operator_hear_operator_write_edges = []
        self.__operator_write_operator_hear_edges = []

    @property
    def operator_hear_vertices(self) -> List[CausalityVertex]:
        return self.__operator_hear_vertices

    @property
    def operator_write_vertices(self) -> List[CausalityVertex]:
        return self.__operator_write_vertices

    @property
    def operator_hear_key_to_operator_hear_vertices(
        self,
    ) -> Dict[str, List[CausalityVertex]]:
        return self.__operator_hear_key_to_operator_hear_vertices

    @property
    def operator_hear_id_to_operator_hear_vertices(
        self,
    ) -> Dict[int, List[CausalityVertex]]:
        return self.__operator_hear_id_to_operator_hear_vertices

    @property
    def operator_hear_operator_write_edges(self) -> List[CausalityEdge]:
        return self.__operator_hear_operator_write_edges

    @property
    def operator_write_operator_hear_edges(self) -> List[CausalityEdge]:
        return self.__operator_write_operator_hear_edges

    def get_operator_hear_with_id(self, operator_hear_id) -> Optional[CausalityVertex]:
        if operator_hear_id in self.operator_hear_id_to_operator_hear_vertices:
            return self.operator_hear_id_to_operator_hear_vertices[operator_hear_id]
        else:
            return None

    def get_prev_operator_hear_with_key(
        self, key, cur_operator_hear_id
    ) -> Optional[CausalityVertex]:
        for i in range(len(self.operator_hear_key_to_operator_hear_vertices[key])):
            operator_hear_vertex = self.operator_hear_key_to_operator_hear_vertices[
                key
            ][i]
            if operator_hear_vertex.content.id == cur_operator_hear_id:
                if i == 0:
                    return None
                else:
                    return self.operator_hear_key_to_operator_hear_vertices[key][i - 1]

    def sanity_check(self):
        # Be careful!!! The operator_hear_id and operator_write_id are only used to differentiate operator_hears/operator_writes
        # the id value does not indicate which operator_hear/operator_write happens earlier/later
        # TODO(xudong): maybe we should also make the id consistent with start_timestamp?
        print("%d operator_hear vertices" % len(self.operator_hear_vertices))
        print("%d operator_write vertices" % len(self.operator_write_vertices))
        print(
            "%d edges from operator_hear to operator_write"
            % len(self.operator_hear_operator_write_edges)
        )
        print(
            "%d edges from operator_write to operator_hear"
            % len(self.operator_write_operator_hear_edges)
        )
        for i in range(len(self.operator_hear_vertices)):
            if i > 0:
                assert (
                    self.operator_hear_vertices[i].gid
                    == self.operator_hear_vertices[i - 1].gid + 1
                )
                assert (
                    self.operator_hear_vertices[i].content.start_timestamp
                    > self.operator_hear_vertices[i - 1].content.start_timestamp
                )
            assert self.operator_hear_vertices[i].is_operator_hear
            for edge in self.operator_hear_vertices[i].out_edges:
                assert self.operator_hear_vertices[i].gid == edge.source.gid
        for i in range(len(self.operator_write_vertices)):
            if i > 0:
                assert (
                    self.operator_write_vertices[i].gid
                    == self.operator_write_vertices[i - 1].gid + 1
                )
                assert (
                    self.operator_write_vertices[i].content.start_timestamp
                    > self.operator_write_vertices[i - 1].content.start_timestamp
                )
            assert self.operator_write_vertices[i].is_operator_write
            for edge in self.operator_write_vertices[i].out_edges:
                assert self.operator_write_vertices[i].gid == edge.source.gid
        for edge in self.operator_hear_operator_write_edges:
            assert isinstance(edge.source, CausalityVertex)
            assert isinstance(edge.sink, CausalityVertex)
            assert edge.source.is_operator_hear() and edge.sink.is_operator_write()
            assert (
                edge.source.content.start_timestamp < edge.sink.content.start_timestamp
            )
        for edge in self.operator_write_operator_hear_edges:
            assert isinstance(edge.source, CausalityVertex)
            assert isinstance(edge.sink, CausalityVertex)
            assert edge.sink.is_operator_hear() and edge.source.is_operator_write()
            assert (
                edge.source.content.start_timestamp < edge.sink.content.start_timestamp
            )

    def add_sorted_operator_hears(self, operator_hear_list: List[OperatorHear]):
        for i in range(len(operator_hear_list)):
            operator_hear = operator_hear_list[i]
            operator_hear_vertex = CausalityVertex(self.__vertex_cnt, operator_hear)
            self.__vertex_cnt += 1
            self.operator_hear_vertices.append(operator_hear_vertex)
            if (
                operator_hear_vertex.content.key
                not in self.operator_hear_key_to_operator_hear_vertices
            ):
                self.operator_hear_key_to_operator_hear_vertices[
                    operator_hear_vertex.content.key
                ] = []
            self.operator_hear_key_to_operator_hear_vertices[
                operator_hear_vertex.content.key
            ].append(operator_hear_vertex)
            assert (
                operator_hear_vertex.content.id
                not in self.operator_hear_id_to_operator_hear_vertices
            )
            self.operator_hear_id_to_operator_hear_vertices[
                operator_hear_vertex.content.id
            ] = operator_hear_vertex

    def add_sorted_operator_writes(self, operator_write_list: List[OperatorWrite]):
        for i in range(len(operator_write_list)):
            operator_write = operator_write_list[i]
            operator_write_vertex = CausalityVertex(self.__vertex_cnt, operator_write)
            self.__vertex_cnt += 1
            self.operator_write_vertices.append(operator_write_vertex)

    def connect_hear_to_write(
        self,
        operator_hear_vertex: CausalityVertex,
        operator_write_vertex: CausalityVertex,
    ):
        assert operator_hear_vertex.is_operator_hear()
        assert operator_write_vertex.is_operator_write()
        assert (
            operator_hear_vertex.content.start_timestamp
            < operator_write_vertex.content.start_timestamp
        )
        edge = CausalityEdge(
            operator_hear_vertex, operator_write_vertex, HEAR_WRITE_EDGE
        )
        operator_hear_vertex.add_out_edge(edge)
        self.operator_hear_operator_write_edges.append(edge)

    def connect_write_to_hear(
        self,
        operator_write_vertex: CausalityVertex,
        operator_hear_vertex: CausalityVertex,
    ):
        assert operator_hear_vertex.is_operator_hear()
        assert operator_write_vertex.is_operator_write()
        assert (
            operator_write_vertex.content.start_timestamp
            < operator_hear_vertex.content.start_timestamp
        )
        edge = CausalityEdge(
            operator_write_vertex, operator_hear_vertex, WRITE_HEAR_EDGE
        )
        operator_write_vertex.add_out_edge(edge)
        self.operator_write_operator_hear_edges.append(edge)


def causality_vertices_connected(source: CausalityVertex, sink: CausalityVertex):
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
