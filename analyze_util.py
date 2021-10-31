import json
from typing import List, Dict, Optional, Union, Set, Tuple
import sieve_config
from controllers import deployment_name
import analyze_event

HEAR_READ_FILTER_FLAG = True
ERROR_MSG_FILTER_FLAG = True

# flags for time travel only
DELETE_ONLY_FILTER_FLAG = True
DELETE_THEN_RECREATE_FLAG = True

# flags for obs gap only
CANCELLABLE_FLAG = True

# flags for atom vio only
READ_BEFORE_WRITE_FLAG = True

ALLOWED_ERROR_TYPE = ["NoError"]

SIEVE_BEFORE_HEAR_MARK = "[SIEVE-BEFORE-EVENT]"
SIEVE_AFTER_HEAR_MARK = "[SIEVE-AFTER-EVENT]"
SIEVE_BEFORE_WRITE_MARK = "[SIEVE-BEFORE-SIDE-EFFECT]"
SIEVE_AFTER_WRITE_MARK = "[SIEVE-AFTER-SIDE-EFFECT]"
SIEVE_AFTER_READ_MARK = "[SIEVE-AFTER-READ]"
SIEVE_BEFORE_RECONCILE_MARK = "[SIEVE-BEFORE-RECONCILE]"
SIEVE_AFTER_RECONCILE_MARK = "[SIEVE-AFTER-RECONCILE]"

SIEVE_API_EVENT_MARK = "[SIEVE-API-EVENT]"

INTER_RECONCILER_EDGE = "INTER-RECONCILER"
INTRA_RECONCILER_EDGE = "INTRA-RECONCILER"

EVENT_NONE_TYPE = "NONE_TYPE"


class APIEventTypes:
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"


class OperatorHearTypes:
    ADDED = "Added"
    UPDATED = "Updated"
    DELETED = "Deleted"
    REPLACED = "Replaced"  # Replaced is emitted when we encountered watch errors and had to do a relist
    SYNC = "Sync"  # Sync is for synthetic events during a periodic resync


class OperatorWriteTypes:
    CREATE = "Create"
    UPDATE = "Update"
    DELETE = "Delete"
    DELETEALLOF = "DeleteAllOf"
    PATCH = "Patch"
    STATUS_UPDATE = "StatusUpdate"
    STATUS_PATCH = "StatusPatch"


# We do not include Sync and Replaced here
detectable_operator_hear_types = [
    OperatorHearTypes.ADDED,
    OperatorHearTypes.UPDATED,
    OperatorHearTypes.DELETED,
]

detectable_operator_write_types = [
    OperatorWriteTypes.CREATE,
    OperatorWriteTypes.UPDATE,
    OperatorWriteTypes.DELETE,
    OperatorWriteTypes.PATCH,
    OperatorWriteTypes.STATUS_UPDATE,
    OperatorWriteTypes.STATUS_PATCH,
]


def consistent_event_type(operator_hear_type: str, operator_write_type: str):
    both_create = (
        operator_hear_type == OperatorHearTypes.ADDED
        and operator_write_type == OperatorWriteTypes.CREATE
    )
    both_update = operator_hear_type == OperatorHearTypes.UPDATED and (
        operator_write_type == OperatorWriteTypes.UPDATE
        or operator_write_type == OperatorWriteTypes.PATCH
        or operator_write_type == OperatorWriteTypes.STATUS_UPDATE
        or operator_write_type == OperatorWriteTypes.STATUS_PATCH
    )
    both_delete = (
        operator_hear_type == OperatorHearTypes.DELETED
        and operator_write_type == OperatorWriteTypes.DELETE
    )
    return both_create or both_update or both_delete


def conflicting_event_type(prev_operator_hear_type: str, cur_operator_hear_type: str):
    other_then_delete = (
        prev_operator_hear_type != OperatorHearTypes.DELETED
        and cur_operator_hear_type == OperatorHearTypes.DELETED
    )
    delete_then_other = (
        prev_operator_hear_type == OperatorHearTypes.DELETED
        and cur_operator_hear_type != OperatorHearTypes.DELETED
    )
    return other_then_delete or delete_then_other


def extract_uid(obj: Dict):
    assert "metadata" in obj, "missing metadata in: " + str(obj)
    obj_uid = obj["metadata"]["uid"] if "uid" in obj["metadata"] else None
    return obj_uid


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


def extract_generate_name(obj: Dict):
    obj_uid = None
    if "metadata" in obj:
        obj_uid = (
            obj["metadata"]["generateName"]
            if "generateName" in obj["metadata"]
            else None
        )
    else:
        obj_uid = obj["generateName"] if "generateName" in obj else None
    return obj_uid


def operator_related_resource(
    project: str, rtype: str, name: str, obj: Dict, taint_list: List[Tuple[str, str]]
):
    depl_name = deployment_name[project]
    if depl_name in name:
        return True
    obj_metadata = obj
    if "metadata" in obj:
        obj_metadata = obj["metadata"]
    if "ownerReferences" in obj_metadata:
        for owner in obj_metadata["ownerReferences"]:
            # if owner["kind"].lower() == "deployment" and owner["name"] == depl_name:
            #     return True
            for taint in taint_list:
                if owner["kind"].lower() == taint[0] and owner["name"] == taint[1]:
                    return True
    return False


def is_generated_random_name(name: str, generate_name: str):
    return name.startswith(generate_name) and len(name) == len(generate_name) + 5


def generate_key(resource_type: str, namespace: str, name: str):
    return "/".join([resource_type, namespace, name])


def api_key_to_rtype_namespace_name(api_key):
    tokens = api_key.split("/")
    assert len(tokens) >= 4
    namespace = tokens[-2]
    name = tokens[-1]
    if tokens[-4] == "services" and tokens[-3] == "endpoints":
        rtype = "endpoints"
    elif tokens[-4] == "services" and tokens[-3] == "specs":
        rtype = "service"
    elif tokens[-3].endswith("s"):
        rtype = tokens[-3][:-1]
    else:
        rtype = tokens[-3]
    return rtype, namespace, name


class APIEvent:
    def __init__(self, etype: str, key: str, obj_str: str):
        self.__etype = etype
        self.__key = key
        assert key.startswith("/")
        self.__rtype, self.__namespace, self.__name = api_key_to_rtype_namespace_name(
            key
        )
        self.__obj_str = obj_str
        self.__obj_map = json.loads(obj_str)

    @property
    def etype(self):
        return self.__etype

    @property
    def key(self):
        return self.__key

    @property
    def rtype(self):
        return self.__rtype

    @property
    def namespace(self):
        return self.__namespace

    @property
    def name(self):
        return self.__name

    @property
    def obj_str(self):
        return self.__obj_str

    @property
    def obj_map(self):
        return self.__obj_map


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
        self.__prev_etype = EVENT_NONE_TYPE
        self.__cancelled_by = set()
        self.__signature_counter = 1

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

    @property
    def signature_counter(self):
        return self.__signature_counter

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

    @signature_counter.setter
    def signature_counter(self, signature_counter: int):
        self.__signature_counter = signature_counter


class OperatorWrite:
    def __init__(self, id: str, etype: str, rtype: str, error: str, obj_str: str):
        self.__id = int(id)
        # do not handle DELETEALLOF for now
        assert etype != OperatorWriteTypes.DELETEALLOF
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
        self.__prev_etype = EVENT_NONE_TYPE
        self.__signature_counter = 1

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

    @property
    def signature_counter(self):
        return self.__signature_counter

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

    @signature_counter.setter
    def signature_counter(self, signature_counter: int):
        self.__signature_counter = signature_counter

    def set_range(self, start_timestamp: int, end_timestamp: int):
        assert start_timestamp < end_timestamp
        self.__range_start_timestamp = start_timestamp
        self.__range_end_timestamp = end_timestamp


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


class ReconcileBegin:
    def __init__(self, controller_name: str, round_id: str):
        self.__controller_name = controller_name
        self.__round_id = round_id
        self.__end_timestamp = -1

    @property
    def controller_name(self):
        return self.__controller_name

    @property
    def round_id(self):
        return self.__round_id

    @property
    def end_timestamp(self):
        return self.__end_timestamp

    @end_timestamp.setter
    def end_timestamp(self, end_timestamp: int):
        self.__end_timestamp = end_timestamp


class ReconcileEnd:
    def __init__(self, controller_name: str, round_id: str):
        self.__controller_name = controller_name
        self.__round_id = round_id
        self.__end_timestamp = -1

    @property
    def controller_name(self):
        return self.__controller_name

    @property
    def round_id(self):
        return self.__round_id

    @property
    def end_timestamp(self):
        return self.__end_timestamp

    @end_timestamp.setter
    def end_timestamp(self, end_timestamp: int):
        self.__end_timestamp = end_timestamp


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


def parse_reconcile(line: str) -> Union[ReconcileBegin, ReconcileEnd]:
    assert SIEVE_BEFORE_RECONCILE_MARK in line or SIEVE_AFTER_RECONCILE_MARK in line
    if SIEVE_BEFORE_RECONCILE_MARK in line:
        tokens = line[line.find(SIEVE_BEFORE_RECONCILE_MARK) :].strip("\n").split("\t")
        return ReconcileBegin(tokens[1], tokens[2])
    else:
        tokens = line[line.find(SIEVE_AFTER_RECONCILE_MARK) :].strip("\n").split("\t")
        return ReconcileEnd(tokens[1], tokens[2])


def parse_api_event(line: str) -> APIEvent:
    assert SIEVE_API_EVENT_MARK in line
    tokens = line[line.find(SIEVE_API_EVENT_MARK) :].strip("\n").split("\t")
    return APIEvent(tokens[1], tokens[2], tokens[3])


def conflicting_event(
    prev_operator_hear: OperatorHear,
    cur_operator_hear: OperatorHear,
    masked_keys: Set[str],
    masked_paths: Set[str],
) -> bool:
    if conflicting_event_type(prev_operator_hear.etype, cur_operator_hear.etype):
        return True
    elif (
        prev_operator_hear.etype != OperatorHearTypes.DELETED
        and cur_operator_hear.etype != OperatorHearTypes.DELETED
        and analyze_event.conflicting_event_payload(
            prev_operator_hear.slim_cur_obj_map,
            cur_operator_hear.obj_map,
            masked_keys,
            masked_paths,
        )
    ):
        return True
    return False


def is_creation_or_deletion(etype: str):
    is_hear_creation_or_deletion = (
        etype == OperatorHearTypes.ADDED or etype == OperatorHearTypes.DELETED
    )
    is_write_creation_or_deletion = (
        etype == OperatorWriteTypes.CREATE or etype == OperatorWriteTypes.DELETE
    )
    return is_hear_creation_or_deletion or is_write_creation_or_deletion


def get_event_signature(event: Union[OperatorHear, OperatorWrite]):
    assert isinstance(event, OperatorHear) or isinstance(event, OperatorWrite)
    signature = (
        event.etype
        if is_creation_or_deletion(event.etype)
        else "\t".join(
            [
                event.etype,
                json.dumps(event.slim_prev_obj_map, sort_keys=True),
                json.dumps(event.slim_cur_obj_map, sort_keys=True),
            ]
        )
    )
    return signature


class CausalityVertex:
    def __init__(
        self,
        gid: int,
        content: Union[
            OperatorHear, OperatorWrite, OperatorRead, ReconcileBegin, ReconcileEnd
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

    def is_operator_read(self) -> bool:
        return isinstance(self.content, OperatorRead)

    def is_reconcile_begin(self) -> bool:
        return isinstance(self.content, ReconcileBegin)

    def is_reconcile_end(self) -> bool:
        return isinstance(self.content, ReconcileEnd)


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
    def __init__(self, learned_masked_paths: Dict, configured_masked: List):
        self.__learned_masked_paths = learned_masked_paths
        self.__configured_masked_paths = set(
            [path for path in configured_masked if not path.startswith("**/")]
        )
        self.__configured_masked_keys = set(
            [path[3:] for path in configured_masked if path.startswith("**/")]
        )
        self.__vertex_cnt = 0
        self.__operator_hear_vertices = []
        self.__operator_write_vertices = []
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
    def operator_hear_vertices(self) -> List[CausalityVertex]:
        return self.__operator_hear_vertices

    @property
    def operator_write_vertices(self) -> List[CausalityVertex]:
        return self.__operator_write_vertices

    @property
    def operator_read_vertices(self) -> List[CausalityVertex]:
        return self.__operator_read_vertices

    @property
    def reconcile_begin_vertices(self) -> List[CausalityVertex]:
        return self.__reconcile_begin_vertices

    @property
    def reconcile_end_vertices(self) -> List[CausalityVertex]:
        return self.__reconcile_end_vertices

    @property
    def operator_read_key_to_vertices(
        self,
    ) -> Dict[str, List[CausalityVertex]]:
        return self.__operator_read_key_to_vertices

    @property
    def operator_write_key_to_vertices(
        self,
    ) -> Dict[str, List[CausalityVertex]]:
        return self.__operator_write_key_to_vertices

    @property
    def operator_hear_key_to_vertices(
        self,
    ) -> Dict[str, List[CausalityVertex]]:
        return self.__operator_hear_key_to_vertices

    @property
    def operator_hear_id_to_vertices(
        self,
    ) -> Dict[int, List[CausalityVertex]]:
        return self.__operator_hear_id_to_vertices

    @property
    def operator_hear_operator_write_edges(self) -> List[CausalityEdge]:
        return self.__operator_hear_operator_write_edges

    @property
    def operator_write_operator_hear_edges(self) -> List[CausalityEdge]:
        return self.__operator_write_operator_hear_edges

    @property
    def intra_reconciler_edges(self) -> List[CausalityEdge]:
        return self.__intra_reconciler_edges

    def retrieve_masked(self, rtype, name):
        masked_keys = set()
        masked_keys.update(self.configured_masked_keys)
        masked_paths = set()
        masked_paths.update(self.configured_masked_paths)
        if rtype in self.learned_masked_paths:
            if name in self.learned_masked_paths[rtype]:
                masked_paths.update(set(self.learned_masked_paths[rtype][name]))
        return (masked_keys, masked_paths)

    def get_operator_hear_with_id(self, operator_hear_id) -> Optional[CausalityVertex]:
        if operator_hear_id in self.operator_hear_id_to_vertices:
            return self.operator_hear_id_to_vertices[operator_hear_id]
        else:
            return None

    def get_prev_operator_hear_with_key(
        self, key, cur_operator_hear_id
    ) -> Optional[CausalityVertex]:
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
            assert self.operator_write_vertices[i].content.range_end_timestamp != -1
            assert (
                self.operator_write_vertices[i].content.range_start_timestamp
                < self.operator_write_vertices[i].content.range_end_timestamp
            )
            assert (
                self.operator_write_vertices[i].content.start_timestamp
                < self.operator_write_vertices[i].content.end_timestamp
            )
            assert (
                self.operator_write_vertices[i].content.end_timestamp
                == self.operator_write_vertices[i].content.range_end_timestamp
            )
            assert self.operator_write_vertices[i].is_operator_write
            for edge in self.operator_write_vertices[i].out_inter_reconciler_edges:
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
            Union[OperatorWrite, OperatorRead, ReconcileBegin, ReconcileEnd]
        ],
    ):
        event_vertex_list = []
        for event in reconciler_event_list:
            event_vertex = CausalityVertex(self.__vertex_cnt, event)
            self.__vertex_cnt += 1
            if event_vertex.is_operator_write():
                self.operator_write_vertices.append(event_vertex)
                key = event_vertex.content.key
                if key not in self.operator_write_key_to_vertices:
                    self.operator_write_key_to_vertices[key] = []
                self.operator_write_key_to_vertices[key].append(event_vertex)
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
            edge = CausalityEdge(prev_vertex, cur_vertex, INTRA_RECONCILER_EDGE)
            prev_vertex.add_out_intra_reconciler_edge(edge)
            self.intra_reconciler_edges.append(edge)

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
            operator_hear_vertex, operator_write_vertex, INTER_RECONCILER_EDGE
        )
        operator_hear_vertex.add_out_inter_reconciler_edge(edge)
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
                masked_keys, masked_paths = self.retrieve_masked(
                    cur_operator_hear.rtype,
                    cur_operator_hear.name,
                )
                slim_prev_object, slim_cur_object = analyze_event.diff_event(
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
                    for i in range(len(self.operator_read_key_to_vertices[key])):
                        operator_read = self.operator_read_key_to_vertices[key][
                            i
                        ].content
                        # if the first read happens after write, break
                        if (
                            i == 0
                            and operator_read.end_timestamp
                            > operator_write.start_timestamp
                        ):
                            break
                        # if this is not the latest read before the write, continue
                        if i != len(self.operator_read_key_to_vertices[key]) - 1:
                            next_operator_read = self.operator_read_key_to_vertices[
                                key
                            ][i + 1].content
                            if (
                                next_operator_read.end_timestamp
                                < operator_write.start_timestamp
                            ):
                                continue

                        assert operator_write.key in operator_read.key_set
                        assert (
                            operator_read.end_timestamp < operator_write.start_timestamp
                        )
                        prev_read_obj_map = operator_read.key_to_obj[key]
                        prev_read_etype = operator_read.etype
                        break
                masked_keys, masked_paths = self.retrieve_masked(
                    operator_write.rtype, operator_write.name
                )
                slim_prev_object, slim_cur_object = analyze_event.diff_event(
                    prev_read_obj_map,
                    operator_write.obj_map,
                    masked_keys,
                    masked_paths,
                    True,
                )
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
                        cur_operator_hear.rtype,
                        cur_operator_hear.name,
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
