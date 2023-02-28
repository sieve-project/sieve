from typing import Dict, List, Optional, Set, Tuple, Union
from sieve_common.k8s_event import (
    ControllerHear,
    ControllerWrite,
    ControllerNonK8sWrite,
    ControllerRead,
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
            ControllerHear,
            ControllerWrite,
            ControllerNonK8sWrite,
            ControllerRead,
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

    def is_controller_hear(self) -> bool:
        return isinstance(self.content, ControllerHear)

    def is_controller_write(self) -> bool:
        return isinstance(self.content, ControllerWrite)

    def is_controller_non_k8s_write(self) -> bool:
        return isinstance(self.content, ControllerNonK8sWrite)

    def is_controller_read(self) -> bool:
        return isinstance(self.content, ControllerRead)

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
        self.__controller_hear_vertices = []
        self.__controller_write_vertices = []
        self.__controller_non_k8s_write_vertices = []
        self.__controller_read_vertices = []
        self.__reconcile_begin_vertices = []
        self.__reconcile_end_vertices = []
        self.__controller_read_key_to_vertices = {}
        self.__controller_write_key_to_vertices = {}
        self.__controller_hear_key_to_vertices = {}
        self.__controller_hear_id_to_vertices = {}
        self.__controller_hear_controller_write_edges = []
        self.__controller_write_controller_hear_edges = []
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
    def controller_hear_vertices(self) -> List[EventVertex]:
        return self.__controller_hear_vertices

    @property
    def controller_write_vertices(self) -> List[EventVertex]:
        return self.__controller_write_vertices

    @property
    def controller_non_k8s_write_vertices(self) -> List[EventVertex]:
        return self.__controller_non_k8s_write_vertices

    @property
    def controller_read_vertices(self) -> List[EventVertex]:
        return self.__controller_read_vertices

    @property
    def reconcile_begin_vertices(self) -> List[EventVertex]:
        return self.__reconcile_begin_vertices

    @property
    def reconcile_end_vertices(self) -> List[EventVertex]:
        return self.__reconcile_end_vertices

    @property
    def controller_read_key_to_vertices(
        self,
    ) -> Dict[str, List[EventVertex]]:
        return self.__controller_read_key_to_vertices

    @property
    def controller_write_key_to_vertices(
        self,
    ) -> Dict[str, List[EventVertex]]:
        return self.__controller_write_key_to_vertices

    @property
    def controller_hear_key_to_vertices(
        self,
    ) -> Dict[str, List[EventVertex]]:
        return self.__controller_hear_key_to_vertices

    @property
    def controller_hear_id_to_vertices(
        self,
    ) -> Dict[int, List[EventVertex]]:
        return self.__controller_hear_id_to_vertices

    @property
    def controller_hear_controller_write_edges(self) -> List[EventEdge]:
        return self.__controller_hear_controller_write_edges

    @property
    def controller_write_controller_hear_edges(self) -> List[EventEdge]:
        return self.__controller_write_controller_hear_edges

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

    def get_controller_hear_with_id(self, controller_hear_id) -> Optional[EventVertex]:
        if controller_hear_id in self.controller_hear_id_to_vertices:
            return self.controller_hear_id_to_vertices[controller_hear_id]
        else:
            return None

    def get_prev_controller_hear_with_key(
        self, key, cur_controller_hear_id
    ) -> Optional[EventVertex]:
        for i in range(len(self.controller_hear_key_to_vertices[key])):
            controller_hear_vertex = self.controller_hear_key_to_vertices[key][i]
            if controller_hear_vertex.content.id == cur_controller_hear_id:
                if i == 0:
                    return None
                else:
                    return self.controller_hear_key_to_vertices[key][i - 1]

    def sanity_check(self):
        # Be careful!!! The controller_hear_id and controller_write_id are only used to differentiate controller_hears/controller_writes
        # the id value does not indicate which controller_hear/controller_write happens earlier/later
        # TODO(xudong): maybe we should also make the id consistent with start_timestamp?
        print("{} controller_hear vertices".format(len(self.controller_hear_vertices)))
        print(
            "{} controller_write vertices".format(len(self.controller_write_vertices))
        )
        print(
            "{} edges from controller_hear to controller_write".format(
                len(self.controller_hear_controller_write_edges)
            )
        )
        print(
            "{} edges from controller_write to controller_hear".format(
                len(self.controller_write_controller_hear_edges)
            )
        )
        for i in range(len(self.controller_hear_vertices)):
            if i > 0:
                assert (
                    self.controller_hear_vertices[i].content.start_timestamp
                    > self.controller_hear_vertices[i - 1].content.start_timestamp
                )
            assert self.controller_hear_vertices[i].is_controller_hear
            assert self.controller_hear_vertices[i].content.start_timestamp != -1
            assert self.controller_hear_vertices[i].content.end_timestamp != -1
            assert (
                self.controller_hear_vertices[i].content.start_timestamp
                < self.controller_hear_vertices[i].content.end_timestamp
            )
            for edge in self.controller_hear_vertices[i].out_inter_reconciler_edges:
                assert self.controller_hear_vertices[i].gid == edge.source.gid
        for i in range(len(self.controller_write_vertices)):
            if i > 0:
                assert (
                    self.controller_write_vertices[i].content.start_timestamp
                    > self.controller_write_vertices[i - 1].content.start_timestamp
                )
            assert (
                self.controller_write_vertices[i].content.start_timestamp
                < self.controller_write_vertices[i].content.end_timestamp
            )
            assert self.controller_write_vertices[i].is_controller_write
            for edge in self.controller_write_vertices[i].out_inter_reconciler_edges:
                assert self.controller_write_vertices[i].gid == edge.source.gid
            if self.controller_write_vertices[i].content.reconcile_id != -1:
                assert (
                    self.controller_write_vertices[i].content.range_end_timestamp != -1
                )
                assert (
                    self.controller_write_vertices[i].content.range_start_timestamp
                    < self.controller_write_vertices[i].content.range_end_timestamp
                )
                assert (
                    self.controller_write_vertices[i].content.end_timestamp
                    == self.controller_write_vertices[i].content.range_end_timestamp
                )
        for edge in self.controller_hear_controller_write_edges:
            assert isinstance(edge.source, EventVertex)
            assert isinstance(edge.sink, EventVertex)
            assert edge.source.is_controller_hear() and edge.sink.is_controller_write()
            assert (
                edge.source.content.start_timestamp < edge.sink.content.start_timestamp
            )
        for edge in self.controller_write_controller_hear_edges:
            assert isinstance(edge.source, EventVertex)
            assert isinstance(edge.sink, EventVertex)
            assert edge.sink.is_controller_hear() and edge.source.is_controller_write()
            assert (
                edge.source.content.start_timestamp < edge.sink.content.start_timestamp
            )

    def add_sorted_controller_hears(self, controller_hear_list: List[ControllerHear]):
        for i in range(len(controller_hear_list)):
            controller_hear = controller_hear_list[i]
            controller_hear_vertex = EventVertex(self.__vertex_cnt, controller_hear)
            self.__vertex_cnt += 1
            self.controller_hear_vertices.append(controller_hear_vertex)
            if (
                controller_hear_vertex.content.key
                not in self.controller_hear_key_to_vertices
            ):
                self.controller_hear_key_to_vertices[
                    controller_hear_vertex.content.key
                ] = []
            self.controller_hear_key_to_vertices[
                controller_hear_vertex.content.key
            ].append(controller_hear_vertex)
            assert (
                controller_hear_vertex.content.id
                not in self.controller_hear_id_to_vertices
            )
            self.controller_hear_id_to_vertices[
                controller_hear_vertex.content.id
            ] = controller_hear_vertex

    def add_sorted_reconciler_events(
        self,
        reconciler_event_list: List[
            Union[
                ControllerWrite,
                ControllerNonK8sWrite,
                ControllerRead,
                ReconcileBegin,
                ReconcileEnd,
            ]
        ],
    ):
        event_vertex_list = []
        for event in reconciler_event_list:
            event_vertex = EventVertex(self.__vertex_cnt, event)
            self.__vertex_cnt += 1
            if event_vertex.is_controller_write():
                self.controller_write_vertices.append(event_vertex)
                key = event_vertex.content.key
                if key not in self.controller_write_key_to_vertices:
                    self.controller_write_key_to_vertices[key] = []
                self.controller_write_key_to_vertices[key].append(event_vertex)
            elif event_vertex.is_controller_non_k8s_write():
                self.controller_non_k8s_write_vertices.append(event_vertex)
            elif event_vertex.is_controller_read():
                self.controller_read_vertices.append(event_vertex)
                for key in event_vertex.content.key_set:
                    if key not in self.controller_read_key_to_vertices:
                        self.controller_read_key_to_vertices[key] = []
                    self.controller_read_key_to_vertices[key].append(event_vertex)
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
        controller_hear_vertex: EventVertex,
        controller_write_vertex: EventVertex,
    ):
        assert controller_hear_vertex.is_controller_hear()
        assert (
            controller_write_vertex.is_controller_write()
            or controller_write_vertex.is_controller_non_k8s_write()
        )
        assert (
            controller_hear_vertex.content.start_timestamp
            < controller_write_vertex.content.start_timestamp
        )
        edge = EventEdge(
            controller_hear_vertex, controller_write_vertex, INTER_RECONCILER_EDGE
        )
        controller_hear_vertex.add_out_inter_reconciler_edge(edge)
        self.controller_hear_controller_write_edges.append(edge)

    def connect_write_to_hear(
        self,
        controller_write_vertex: EventVertex,
        controller_hear_vertex: EventVertex,
    ):
        assert controller_hear_vertex.is_controller_hear()
        assert controller_write_vertex.is_controller_write()
        assert (
            controller_write_vertex.content.start_timestamp
            < controller_hear_vertex.content.start_timestamp
        )
        edge = EventEdge(
            controller_write_vertex, controller_hear_vertex, INTER_RECONCILER_EDGE
        )
        controller_write_vertex.add_out_inter_reconciler_edge(edge)
        self.controller_write_controller_hear_edges.append(edge)

    def compute_event_diff(self):
        for key in self.controller_hear_key_to_vertices:
            vertices = self.controller_hear_key_to_vertices[key]
            event_signature_to_counter = {}
            prev_hear_obj_map = {}
            prev_hear_etype = EVENT_NONE_TYPE
            for i in range(len(vertices)):
                cur_controller_hear = vertices[i].content
                if not i == 0:
                    prev_controller_hear = vertices[i - 1].content
                    prev_hear_obj_map = prev_controller_hear.obj_map
                    prev_hear_etype = prev_controller_hear.etype
                masked_keys, masked_paths = self.retrieve_masked(
                    cur_controller_hear.key
                )
                slim_prev_object, slim_cur_object = diff_event(
                    prev_hear_obj_map,
                    cur_controller_hear.obj_map,
                    masked_keys,
                    masked_paths,
                )
                cur_controller_hear.slim_prev_obj_map = slim_prev_object
                cur_controller_hear.slim_cur_obj_map = slim_cur_object
                cur_controller_hear.prev_etype = prev_hear_etype
                event_signature = get_event_signature(cur_controller_hear)
                if event_signature not in event_signature_to_counter:
                    event_signature_to_counter[event_signature] = 0
                event_signature_to_counter[event_signature] += 1
                cur_controller_hear.signature_counter = event_signature_to_counter[
                    event_signature
                ]

        for key in self.controller_write_key_to_vertices:
            vertices = self.controller_write_key_to_vertices[key]
            event_signature_to_counter = {}
            for controller_write_vertex in vertices:
                prev_read_obj_map = {}
                prev_read_etype = EVENT_NONE_TYPE
                controller_write = controller_write_vertex.content
                key = controller_write.key
                if key in self.controller_read_key_to_vertices:
                    for controller_read_vertex in self.controller_read_key_to_vertices[
                        key
                    ]:
                        controller_read = controller_read_vertex.content
                        # TODO: we should only consider the read in the same reconcile round as the write
                        # if the read happens after write, break
                        if (
                            controller_read.end_timestamp
                            > controller_write.start_timestamp
                        ):
                            break
                        assert controller_write.key in controller_read.key_set
                        assert (
                            controller_read.end_timestamp
                            < controller_write.start_timestamp
                        )
                        if (
                            controller_read.reconcile_fun
                            == controller_write.reconcile_fun
                            and controller_read.reconcile_id
                            == controller_write.reconcile_id
                        ):
                            prev_read_obj_map = controller_read.key_to_obj[key]
                            prev_read_etype = controller_read.etype

                masked_keys, masked_paths = self.retrieve_masked(controller_write.key)
                slim_prev_object, slim_cur_object = diff_event(
                    prev_read_obj_map,
                    controller_write.obj_map,
                    masked_keys,
                    masked_paths,
                    True,
                )
                controller_write.prev_obj_map = prev_read_obj_map
                controller_write.slim_prev_obj_map = slim_prev_object
                controller_write.slim_cur_obj_map = slim_cur_object
                controller_write.prev_etype = prev_read_etype
                event_signature = get_event_signature(controller_write)
                if event_signature not in event_signature_to_counter:
                    event_signature_to_counter[event_signature] = 0
                event_signature_to_counter[event_signature] += 1
                controller_write.signature_counter = event_signature_to_counter[
                    event_signature
                ]

        non_k8s_signature_counter_map = {}
        for controller_non_k8s_write in self.controller_non_k8s_write_vertices:
            signature = (
                controller_non_k8s_write.content.recv_type
                + "/"
                + controller_non_k8s_write.content.fun_name
            )
            if signature not in non_k8s_signature_counter_map:
                non_k8s_signature_counter_map[signature] = 0
            non_k8s_signature_counter_map[signature] += 1
            controller_non_k8s_write.content.signature_counter = (
                non_k8s_signature_counter_map[signature]
            )

    def compute_event_cancel(self):
        for key in self.controller_hear_key_to_vertices:
            for i in range(len(self.controller_hear_key_to_vertices[key]) - 1):
                cancelled_by = set()
                cur_controller_hear = self.controller_hear_key_to_vertices[key][
                    i
                ].content
                for j in range(i + 1, len(self.controller_hear_key_to_vertices[key])):
                    future_controller_hear = self.controller_hear_key_to_vertices[key][
                        j
                    ].content
                    # TODO: why do we always add the future_controller_hear when i == 0?
                    if i == 0:
                        cancelled_by.add(future_controller_hear.id)
                        continue
                    masked_keys, masked_paths = self.retrieve_masked(
                        cur_controller_hear.key
                    )
                    if conflicting_event(
                        cur_controller_hear,
                        future_controller_hear,
                        masked_keys,
                        masked_paths,
                    ):
                        cancelled_by.add(future_controller_hear.id)
                cur_controller_hear.cancelled_by = cancelled_by

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
