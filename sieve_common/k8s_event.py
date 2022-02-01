import json
from typing import Dict, List, Set, Tuple, Union

from sieve_common.event_delta import conflicting_event_payload

HEAR_READ_FILTER_FLAG = True
ERROR_MSG_FILTER_FLAG = True

# flags for stale state only
DELETE_ONLY_FILTER_FLAG = True
DELETE_THEN_RECREATE_FLAG = True

# flags for unobserved state only
CANCELLABLE_FLAG = True

# flags for intermediate state only
READ_BEFORE_WRITE_FLAG = True

ALLOWED_ERROR_TYPE = ["NoError"]

SIEVE_BEFORE_HEAR_MARK = "[SIEVE-BEFORE-HEAR]"
SIEVE_AFTER_HEAR_MARK = "[SIEVE-AFTER-HEAR]"
SIEVE_BEFORE_WRITE_MARK = "[SIEVE-BEFORE-WRITE]"
SIEVE_AFTER_WRITE_MARK = "[SIEVE-AFTER-WRITE]"
SIEVE_AFTER_READ_MARK = "[SIEVE-AFTER-READ]"
SIEVE_BEFORE_RECONCILE_MARK = "[SIEVE-BEFORE-RECONCILE]"
SIEVE_AFTER_RECONCILE_MARK = "[SIEVE-AFTER-RECONCILE]"

SIEVE_API_EVENT_MARK = "[SIEVE-API-EVENT]"

EVENT_NONE_TYPE = "NONE_TYPE"

DEFAULT_NS = "default"


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
    # TODO: we should allow namespace other than default here
    obj_name = obj["metadata"]["name"]
    obj_namespace = (
        obj["metadata"]["namespace"] if "namespace" in obj["metadata"] else "default"
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
    project: str,
    rtype: str,
    name: str,
    obj: Dict,
    taint_list: List[Tuple[str, str]],
    deployment_name,
):
    if deployment_name in name:
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
    # TODO: get rid of the dirty hack for getting resource type
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
    def __init__(
        self,
        id: str,
        etype: str,
        rtype: str,
        reconciler_type: str,
        error: str,
        obj_str: str,
    ):
        self.__id = int(id)
        # do not handle DELETEALLOF for now
        assert etype != OperatorWriteTypes.DELETEALLOF
        self.__etype = etype
        self.__rtype = rtype
        self.__reconciler_type = reconciler_type
        self.__reconcile_id = -1
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
        self.__prev_obj_map = None
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
    def reconciler_type(self):
        return self.__reconciler_type

    @property
    def reconcile_id(self):
        return self.__reconcile_id

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
    def prev_obj_map(self):
        return self.__prev_obj_map

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

    @reconcile_id.setter
    def reconcile_id(self, reconcile_id: int):
        self.__reconcile_id = reconcile_id

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

    @prev_obj_map.setter
    def prev_obj_map(self, prev_obj_map: Dict):
        self.__prev_obj_map = prev_obj_map

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
        from_cache: str,
        rtype: str,
        namespace: str,
        name: str,
        reconciler_type: str,
        error: str,
        obj_str: str,
    ):
        self.__etype = etype
        self.__from_cache = True if from_cache == "true" else False
        self.__rtype = rtype
        self.__reconciler_type = reconciler_type
        self.__reconcile_id = -1
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
                    self.rtype,
                    obj["metadata"]["namespace"]
                    if "namespace" in obj["metadata"]
                    else DEFAULT_NS,
                    obj["metadata"]["name"],
                )
                assert key not in self.key_set
                assert key not in self.key_to_obj
                self.key_set.add(key)
                self.key_to_obj[key] = obj

    @property
    def etype(self):
        return self.__etype

    @property
    def from_cache(self):
        return self.__from_cache

    @property
    def rtype(self):
        return self.__rtype

    @property
    def reconciler_type(self):
        return self.__reconciler_type

    @property
    def reconcile_id(self):
        return self.__reconcile_id

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

    @reconcile_id.setter
    def reconcile_id(self, reconcile_id: int):
        self.__reconcile_id = reconcile_id


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
    def __init__(self, reconciler_type: str, reconcile_id: str):
        self.__reconciler_type = reconciler_type
        self.__reconcile_id = reconcile_id
        self.__end_timestamp = -1

    @property
    def reconciler_type(self):
        return self.__reconciler_type

    @property
    def reconcile_id(self):
        return self.__reconcile_id

    @property
    def end_timestamp(self):
        return self.__end_timestamp

    @end_timestamp.setter
    def end_timestamp(self, end_timestamp: int):
        self.__end_timestamp = end_timestamp


class ReconcileEnd:
    def __init__(self, reconciler_type: str, reconcile_id: str):
        self.__reconciler_type = reconciler_type
        self.__reconcile_id = reconcile_id
        self.__end_timestamp = -1

    @property
    def reconciler_type(self):
        return self.__reconciler_type

    @property
    def reconcile_id(self):
        return self.__reconcile_id

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
    return OperatorWrite(
        tokens[1], tokens[2], tokens[3], tokens[4], tokens[5], tokens[6]
    )


def parse_operator_read(line: str) -> OperatorRead:
    assert SIEVE_AFTER_READ_MARK in line
    tokens = line[line.find(SIEVE_AFTER_READ_MARK) :].strip("\n").split("\t")
    if tokens[1] == "Get":
        return OperatorRead(
            tokens[1],
            tokens[2],
            tokens[3],
            tokens[4],
            tokens[5],
            tokens[6],
            tokens[7],
            tokens[8],
        )
    elif tokens[1] == "List":
        # When using List, the resource type is like xxxlist so we need to trim the last four characters here
        assert tokens[3].endswith("list")
        return OperatorRead(
            tokens[1],
            tokens[2],
            tokens[3][:-4],
            "",
            "",
            tokens[4],
            tokens[5],
            tokens[6],
        )
    else:
        assert False, "read type should be: Get, List"


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
        and conflicting_event_payload(
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
