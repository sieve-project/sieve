from typing import Dict, List, Optional, Set, Tuple, Union
from sieve_common.k8s_event import (
    OperatorHear,
    OperatorWrite,
    OperatorNonK8sWrite,
    OperatorRead,
    ReconcileBegin,
    ReconcileEnd,
    EVENT_NONE_TYPE,
    generate_key,
    get_event_signature,
    conflicting_event,
    get_mask_by_resource_key,
    parse_key,
)
from sieve_common.event_delta import diff_event

INTER_RECONCILER_EDGE = "INTER-RECONCILER"
INTRA_RECONCILER_EDGE = "INTRA-RECONCILER"


class EventVertex:
    def __init__(
        self,
        gid: int,
        content: Union[
            OperatorHear,
            OperatorWrite,
            OperatorNonK8sWrite,
            OperatorRead,
            ReconcileBegin,
            ReconcileEnd,
        ],
    ):
        self.__gid = gid
        self.__content = content
        self.__out_inter_reconciler_edges = []
        self.__out_intra_reconciler_edges = []

    @property
    def gid(self):
        return self.__gid

    @property
    def content(self):
        return self.__content

    @property
    def out_inter_reconciler_edges(self) -> List:
        return self.__out_inter_reconciler_edges

    @property
    def out_intra_reconciler_edges(self) -> List:
        return self.__out_intra_reconciler_edges

    def add_out_inter_reconciler_edge(self, edge):
        self.out_inter_reconciler_edges.append(edge)

    def add_out_intra_reconciler_edge(self, edge):
        self.out_intra_reconciler_edges.append(edge)

    def is_operator_hear(self) -> bool:
        return isinstance(self.content, OperatorHear)

    def is_operator_write(self) -> bool:
        return isinstance(self.content, OperatorWrite)

    def is_operator_non_k8s_write(self) -> bool:
        return isinstance(self.content, OperatorNonK8sWrite)

    def is_operator_read(self) -> bool:
        return isinstance(self.content, OperatorRead)

    def is_reconcile_begin(self) -> bool:
        return isinstance(self.content, ReconcileBegin)

    def is_reconcile_end(self) -> bool:
        return isinstance(self.content, ReconcileEnd)


class EventEdge:
    def __init__(self, source: EventVertex, sink: EventVertex, type: str):
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


class EventGraph:
    def __init__(
        self,
        learned_masked_paths: Dict,
        configured_masked_keys: Dict,
        configured_masked_paths: Dict,
    ):
        self.__learned_masked_paths = learned_masked_paths
        self.__configured_masked_keys = configured_masked_keys
        self.__configured_masked_paths = configured_masked_paths
        self.__vertex_cnt = 0
        self.__operator_hear_vertices = []
        self.__operator_write_vertices = []
        self.__operator_non_k8s_write_vertices = []
        self.__operator_read_vertices = []
        self.__reconcile_begin_vertices = []
        self.__reconcile_end_vertices = []
        self.__operator_read_key_to_vertices = {}
        self.__operator_write_key_to_vertices = {}
        self.__operator_hear_key_to_vertices = {}
        self.__operator_hear_id_to_vertices = {}
        self.__operator_hear_operator_write_edges = []
        self.__operator_write_operator_hear_edges = []
        self.__intra_reconciler_edges = []

    @property
    def learned_masked_paths(self) -> Dict:
        return self.__learned_masked_paths

    @property
    def configured_masked_paths(self) -> Set[str]:
        return self.__configured_masked_paths

    @property
    def configured_masked_keys(self) -> Set[str]:
        return self.__configured_masked_keys

    @property
    def operator_hear_vertices(self) -> List[EventVertex]:
        return self.__operator_hear_vertices

    @property
    def operator_write_vertices(self) -> List[EventVertex]:
        return self.__operator_write_vertices

    @property
    def operator_non_k8s_write_vertices(self) -> List[EventVertex]:
        return self.__operator_non_k8s_write_vertices

    @property
    def operator_read_vertices(self) -> List[EventVertex]:
        return self.__operator_read_vertices

    @property
    def reconcile_begin_vertices(self) -> List[EventVertex]:
        return self.__reconcile_begin_vertices

    @property
    def reconcile_end_vertices(self) -> List[EventVertex]:
        return self.__reconcile_end_vertices

    @property
    def operator_read_key_to_vertices(
        self,
    ) -> Dict[str, List[EventVertex]]:
        return self.__operator_read_key_to_vertices

    @property
    def operator_write_key_to_vertices(
        self,
    ) -> Dict[str, List[EventVertex]]:
        return self.__operator_write_key_to_vertices

    @property
    def operator_hear_key_to_vertices(
        self,
    ) -> Dict[str, List[EventVertex]]:
        return self.__operator_hear_key_to_vertices

    @property
    def operator_hear_id_to_vertices(
        self,
    ) -> Dict[int, List[EventVertex]]:
        return self.__operator_hear_id_to_vertices

    @property
    def operator_hear_operator_write_edges(self) -> List[EventEdge]:
        return self.__operator_hear_operator_write_edges

    @property
    def operator_write_operator_hear_edges(self) -> List[EventEdge]:
        return self.__operator_write_operator_hear_edges

    @property
    def intra_reconciler_edges(self) -> List[EventEdge]:
        return self.__intra_reconciler_edges

    def retrieve_masked(self, resource_key):
        masked_keys = set()
        masked_keys.update(
            set(get_mask_by_resource_key(self.configured_masked_keys, resource_key))
        )
        masked_paths = set()
        masked_paths.update(
            set(get_mask_by_resource_key(self.configured_masked_paths, resource_key))
        )
        masked_paths.update(
            set(get_mask_by_resource_key(self.learned_masked_paths, resource_key))
        )
        return (masked_keys, masked_paths)

    def get_operator_hear_with_id(self, operator_hear_id) -> Optional[EventVertex]:
        if operator_hear_id in self.operator_hear_id_to_vertices:
            return self.operator_hear_id_to_vertices[operator_hear_id]
        else:
            return None

    def get_prev_operator_hear_with_key(
        self, key, cur_operator_hear_id
    ) -> Optional[EventVertex]:
        for i in range(len(self.operator_hear_key_to_vertices[key])):
            operator_hear_vertex = self.operator_hear_key_to_vertices[key][i]
            if operator_hear_vertex.content.id == cur_operator_hear_id:
                if i == 0:
                    return None
                else:
                    return self.operator_hear_key_to_vertices[key][i - 1]

    def sanity_check(self):
        # Be careful!!! The operator_hear_id and operator_write_id are only used to differentiate operator_hears/operator_writes
        # the id value does not indicate which operator_hear/operator_write happens earlier/later
        # TODO(xudong): maybe we should also make the id consistent with start_timestamp?
        print("{} operator_hear vertices".format(len(self.operator_hear_vertices)))
        print("{} operator_write vertices".format(len(self.operator_write_vertices)))
        print(
            "{} edges from operator_hear to operator_write".format(
                len(self.operator_hear_operator_write_edges)
            )
        )
        print(
            "{} edges from operator_write to operator_hear".format(
                len(self.operator_write_operator_hear_edges)
            )
        )
        for i in range(len(self.operator_hear_vertices)):
            if i > 0:
                assert (
                    self.operator_hear_vertices[i].content.start_timestamp
                    > self.operator_hear_vertices[i - 1].content.start_timestamp
                )
            assert self.operator_hear_vertices[i].is_operator_hear
            assert self.operator_hear_vertices[i].content.start_timestamp != -1
            assert self.operator_hear_vertices[i].content.end_timestamp != -1
            assert (
                self.operator_hear_vertices[i].content.start_timestamp
                < self.operator_hear_vertices[i].content.end_timestamp
            )
            for edge in self.operator_hear_vertices[i].out_inter_reconciler_edges:
                assert self.operator_hear_vertices[i].gid == edge.source.gid
        for i in range(len(self.operator_write_vertices)):
            if i > 0:
                assert (
                    self.operator_write_vertices[i].content.start_timestamp
                    > self.operator_write_vertices[i - 1].content.start_timestamp
                )
            assert (
                self.operator_write_vertices[i].content.start_timestamp
                < self.operator_write_vertices[i].content.end_timestamp
            )
            assert self.operator_write_vertices[i].is_operator_write
            for edge in self.operator_write_vertices[i].out_inter_reconciler_edges:
                assert self.operator_write_vertices[i].gid == edge.source.gid
            if self.operator_write_vertices[i].content.reconcile_id != -1:
                assert self.operator_write_vertices[i].content.range_end_timestamp != -1
                assert (
                    self.operator_write_vertices[i].content.range_start_timestamp
                    < self.operator_write_vertices[i].content.range_end_timestamp
                )
                assert (
                    self.operator_write_vertices[i].content.end_timestamp
                    == self.operator_write_vertices[i].content.range_end_timestamp
                )
        for edge in self.operator_hear_operator_write_edges:
            assert isinstance(edge.source, EventVertex)
            assert isinstance(edge.sink, EventVertex)
            assert edge.source.is_operator_hear() and edge.sink.is_operator_write()
            assert (
                edge.source.content.start_timestamp < edge.sink.content.start_timestamp
            )
        for edge in self.operator_write_operator_hear_edges:
            assert isinstance(edge.source, EventVertex)
            assert isinstance(edge.sink, EventVertex)
            assert edge.sink.is_operator_hear() and edge.source.is_operator_write()
            assert (
                edge.source.content.start_timestamp < edge.sink.content.start_timestamp
            )

    def add_sorted_operator_hears(self, operator_hear_list: List[OperatorHear]):
        for i in range(len(operator_hear_list)):
            operator_hear = operator_hear_list[i]
            operator_hear_vertex = EventVertex(self.__vertex_cnt, operator_hear)
            self.__vertex_cnt += 1
            self.operator_hear_vertices.append(operator_hear_vertex)
            if (
                operator_hear_vertex.content.key
                not in self.operator_hear_key_to_vertices
            ):
                self.operator_hear_key_to_vertices[
                    operator_hear_vertex.content.key
                ] = []
            self.operator_hear_key_to_vertices[operator_hear_vertex.content.key].append(
                operator_hear_vertex
            )
            assert (
                operator_hear_vertex.content.id not in self.operator_hear_id_to_vertices
            )
            self.operator_hear_id_to_vertices[
                operator_hear_vertex.content.id
            ] = operator_hear_vertex

    def add_sorted_reconciler_events(
        self,
        reconciler_event_list: List[
            Union[
                OperatorWrite,
                OperatorNonK8sWrite,
                OperatorRead,
                ReconcileBegin,
                ReconcileEnd,
            ]
        ],
    ):
        event_vertex_list = []
        for event in reconciler_event_list:
            event_vertex = EventVertex(self.__vertex_cnt, event)
            self.__vertex_cnt += 1
            if event_vertex.is_operator_write():
                self.operator_write_vertices.append(event_vertex)
                key = event_vertex.content.key
                if key not in self.operator_write_key_to_vertices:
                    self.operator_write_key_to_vertices[key] = []
                self.operator_write_key_to_vertices[key].append(event_vertex)
            elif event_vertex.is_operator_non_k8s_write():
                self.operator_non_k8s_write_vertices.append(event_vertex)
            elif event_vertex.is_operator_read():
                self.operator_read_vertices.append(event_vertex)
                for key in event_vertex.content.key_set:
                    if key not in self.operator_read_key_to_vertices:
                        self.operator_read_key_to_vertices[key] = []
                    self.operator_read_key_to_vertices[key].append(event_vertex)
            elif event_vertex.is_reconcile_begin():
                self.reconcile_begin_vertices.append(event_vertex)
            elif event_vertex.is_reconcile_end():
                self.reconcile_end_vertices.append(event_vertex)
            else:
                assert False
            event_vertex_list.append(event_vertex)
        for i in range(1, len(event_vertex_list)):
            prev_vertex = event_vertex_list[i - 1]
            cur_vertex = event_vertex_list[i]
            edge = EventEdge(prev_vertex, cur_vertex, INTRA_RECONCILER_EDGE)
            prev_vertex.add_out_intra_reconciler_edge(edge)
            self.intra_reconciler_edges.append(edge)

    def connect_hear_to_write(
        self,
        operator_hear_vertex: EventVertex,
        operator_write_vertex: EventVertex,
    ):
        assert operator_hear_vertex.is_operator_hear()
        assert (
            operator_write_vertex.is_operator_write()
            or operator_write_vertex.is_operator_non_k8s_write()
        )
        assert (
            operator_hear_vertex.content.start_timestamp
            < operator_write_vertex.content.start_timestamp
        )
        edge = EventEdge(
            operator_hear_vertex, operator_write_vertex, INTER_RECONCILER_EDGE
        )
        operator_hear_vertex.add_out_inter_reconciler_edge(edge)
        self.operator_hear_operator_write_edges.append(edge)

    def connect_write_to_hear(
        self,
        operator_write_vertex: EventVertex,
        operator_hear_vertex: EventVertex,
    ):
        assert operator_hear_vertex.is_operator_hear()
        assert operator_write_vertex.is_operator_write()
        assert (
            operator_write_vertex.content.start_timestamp
            < operator_hear_vertex.content.start_timestamp
        )
        edge = EventEdge(
            operator_write_vertex, operator_hear_vertex, INTER_RECONCILER_EDGE
        )
        operator_write_vertex.add_out_inter_reconciler_edge(edge)
        self.operator_write_operator_hear_edges.append(edge)

    def compute_event_diff(self):
        for key in self.operator_hear_key_to_vertices:
            vertices = self.operator_hear_key_to_vertices[key]
            event_signature_to_counter = {}
            prev_hear_obj_map = {}
            prev_hear_etype = EVENT_NONE_TYPE
            for i in range(len(vertices)):
                cur_operator_hear = vertices[i].content
                if not i == 0:
                    prev_operator_hear = vertices[i - 1].content
                    prev_hear_obj_map = prev_operator_hear.obj_map
                    prev_hear_etype = prev_operator_hear.etype
                masked_keys, masked_paths = self.retrieve_masked(cur_operator_hear.key)
                slim_prev_object, slim_cur_object = diff_event(
                    prev_hear_obj_map,
                    cur_operator_hear.obj_map,
                    masked_keys,
                    masked_paths,
                )
                cur_operator_hear.slim_prev_obj_map = slim_prev_object
                cur_operator_hear.slim_cur_obj_map = slim_cur_object
                cur_operator_hear.prev_etype = prev_hear_etype
                event_signature = get_event_signature(cur_operator_hear)
                if event_signature not in event_signature_to_counter:
                    event_signature_to_counter[event_signature] = 0
                event_signature_to_counter[event_signature] += 1
                cur_operator_hear.signature_counter = event_signature_to_counter[
                    event_signature
                ]

        for key in self.operator_write_key_to_vertices:
            vertices = self.operator_write_key_to_vertices[key]
            event_signature_to_counter = {}
            for operator_write_vertex in vertices:
                prev_read_obj_map = {}
                prev_read_etype = EVENT_NONE_TYPE
                operator_write = operator_write_vertex.content
                key = operator_write.key
                if key in self.operator_read_key_to_vertices:
                    for operator_read_vertex in self.operator_read_key_to_vertices[key]:
                        operator_read = operator_read_vertex.content
                        # TODO: we should only consider the read in the same reconcile round as the write
                        # if the read happens after write, break
                        if operator_read.end_timestamp > operator_write.start_timestamp:
                            break
                        assert operator_write.key in operator_read.key_set
                        assert (
                            operator_read.end_timestamp < operator_write.start_timestamp
                        )
                        if (
                            operator_read.reconcile_fun == operator_write.reconcile_fun
                            and operator_read.reconcile_id
                            == operator_write.reconcile_id
                        ):
                            prev_read_obj_map = operator_read.key_to_obj[key]
                            prev_read_etype = operator_read.etype

                masked_keys, masked_paths = self.retrieve_masked(operator_write.key)
                slim_prev_object, slim_cur_object = diff_event(
                    prev_read_obj_map,
                    operator_write.obj_map,
                    masked_keys,
                    masked_paths,
                    True,
                )
                operator_write.prev_obj_map = prev_read_obj_map
                operator_write.slim_prev_obj_map = slim_prev_object
                operator_write.slim_cur_obj_map = slim_cur_object
                operator_write.prev_etype = prev_read_etype
                event_signature = get_event_signature(operator_write)
                if event_signature not in event_signature_to_counter:
                    event_signature_to_counter[event_signature] = 0
                event_signature_to_counter[event_signature] += 1
                operator_write.signature_counter = event_signature_to_counter[
                    event_signature
                ]

        non_k8s_signature_counter_map = {}
        for operator_non_k8s_write in self.operator_non_k8s_write_vertices:
            signature = (
                operator_non_k8s_write.content.recv_type
                + "/"
                + operator_non_k8s_write.content.fun_name
            )
            if signature not in non_k8s_signature_counter_map:
                non_k8s_signature_counter_map[signature] = 0
            non_k8s_signature_counter_map[signature] += 1
            operator_non_k8s_write.content.signature_counter = (
                non_k8s_signature_counter_map[signature]
            )

    def compute_event_cancel(self):
        for key in self.operator_hear_key_to_vertices:
            for i in range(len(self.operator_hear_key_to_vertices[key]) - 1):
                cancelled_by = set()
                cur_operator_hear = self.operator_hear_key_to_vertices[key][i].content
                for j in range(i + 1, len(self.operator_hear_key_to_vertices[key])):
                    future_operator_hear = self.operator_hear_key_to_vertices[key][
                        j
                    ].content
                    # TODO: why do we always add the future_operator_hear when i == 0?
                    if i == 0:
                        cancelled_by.add(future_operator_hear.id)
                        continue
                    masked_keys, masked_paths = self.retrieve_masked(
                        cur_operator_hear.key
                    )
                    if conflicting_event(
                        cur_operator_hear,
                        future_operator_hear,
                        masked_keys,
                        masked_paths,
                    ):
                        cancelled_by.add(future_operator_hear.id)
                cur_operator_hear.cancelled_by = cancelled_by

    def finalize(self):
        self.compute_event_diff()
        self.compute_event_cancel()


def event_vertices_reachable(source: EventVertex, sink: EventVertex):
    # there should be no cycles in the casuality graph
    queue = []
    visited = set()
    queue.append(source)
    visited.add(source.gid)
    if source.gid == sink.gid:
        return True
    while len(queue) != 0:
        cur = queue.pop(0)
        for edge in cur.out_inter_reconciler_edges:
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


def event_vertices_connected(source: EventVertex, sink: EventVertex):
    for edge in source.out_inter_reconciler_edges:
        if edge.sink.gid == sink.gid:
            return True
    return False
