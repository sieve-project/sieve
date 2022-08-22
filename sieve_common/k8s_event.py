import json
import resource
from typing import Dict, List, Set, Union
from pathlib import PurePath
from sieve_common.event_delta import conflicting_event_payload

HEAR_READ_FILTER_FLAG = True
ERROR_MSG_FILTER_FLAG = True


ALLOWED_ERROR_TYPE = ["NoError"]

SIEVE_BEFORE_HEAR_MARK = "[SIEVE-BEFORE-HEAR]"
SIEVE_AFTER_HEAR_MARK = "[SIEVE-AFTER-HEAR]"
SIEVE_BEFORE_REST_WRITE_MARK = "[SIEVE-BEFORE-REST-WRITE]"
SIEVE_AFTER_REST_WRITE_MARK = "[SIEVE-AFTER-REST-WRITE]"
SIEVE_AFTER_CACHE_READ_MARK = "[SIEVE-AFTER-CACHE-READ]"
SIEVE_BEFORE_RECONCILE_MARK = "[SIEVE-BEFORE-RECONCILE]"
SIEVE_AFTER_RECONCILE_MARK = "[SIEVE-AFTER-RECONCILE]"
SIEVE_BEFORE_ANNOTATED_API_INVOCATION_MARK = "[SIEVE-BEFORE-ANNOTATED-API-INVOCATION]"
SIEVE_AFTER_ANNOTATED_API_INVOCATION_MARK = "[SIEVE-AFTER-ANNOTATED-API-INVOCATION]"

SIEVE_API_EVENT_MARK = "[SIEVE-API-EVENT]"

EVENT_NONE_TYPE = "NONE_TYPE"
NON_K8S_WRITE = "NON_K8S_WRITE"

DEFAULT_NS = "default"

UNKNOWN_RECONCILER_TYPE = "unknown"


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


def extract_name(obj: Dict):
    assert "metadata" in obj, "missing metadata in: " + str(obj)
    # TODO: we should allow namespace other than default here
    obj_name = obj["metadata"]["name"]
    return obj_name


def extract_generate_name(obj: Dict):
    obj_generate_name = None
    if "metadata" in obj:
        obj_generate_name = (
            obj["metadata"]["generateName"]
            if "generateName" in obj["metadata"]
            else None
        )
    else:
        obj_generate_name = obj["generateName"] if "generateName" in obj else None
    return obj_generate_name


# def operator_related_resource(
#     project: str,
#     rtype: str,
#     name: str,
#     obj: Dict,
#     taint_list: List[Tuple[str, str]],
#     deployment_name,
# ):
#     if deployment_name in name:
#         return True
#     obj_metadata = obj
#     if "metadata" in obj:
#         obj_metadata = obj["metadata"]
#     if "ownerReferences" in obj_metadata:
#         for owner in obj_metadata["ownerReferences"]:
#             # if owner["kind"].lower() == "deployment" and owner["name"] == depl_name:
#             #     return True
#             for taint in taint_list:
#                 if owner["kind"].lower() == taint[0] and owner["name"] == taint[1]:
#                     return True
#     return False


def is_generated_random_name(name: str, generate_name: str):
    return name.startswith(generate_name) and len(name) == len(generate_name) + 5


def generate_key(resource_type: str, namespace: str, name: str):
    return "/".join([resource_type, namespace, name])


def parse_key(key: str):
    tokens = key.split("/")
    assert len(tokens) == 3
    return tokens[0], tokens[1], tokens[2]


def get_mask_by_resource_key(key_mask_map, resource_key):
    # TODO: converting the list to a string may lead to ambiguity
    # consider two lists: ["a", "b", "c"] and ["a/b", "c"]
    # after converting to string they look the same
    masked_keys = []
    for key in key_mask_map:
        if key == resource_key or PurePath("/" + resource_key).match("/" + key):
            for field_path_list in key_mask_map[key]:
                assert isinstance(field_path_list, List)
                assert len(field_path_list) > 0
                if len(field_path_list) == 1:
                    masked_keys.append(field_path_list[0])
                else:
                    masked_keys.append("/".join(field_path_list))
    return masked_keys


class APIEvent:
    def __init__(
        self,
        etype: str,
        orignal_key: str,
        rtype: str,
        namespace: str,
        name: str,
        obj_str: str,
    ):
        self.__etype = etype
        self.__original_key = orignal_key
        self.__key = generate_key(rtype, namespace, name)
        self.__rtype = rtype
        self.__namespace = namespace
        self.__name = name
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

    def get_metadata_value(self, mkey):
        if mkey in self.obj_map:
            return self.obj_map[mkey]
        elif "metadata" in self.obj_map and mkey in self.obj_map["metadata"]:
            return self.obj_map["metadata"][mkey]
        else:
            return None


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


class OperatorNonK8sWrite:
    def __init__(
        self,
        id: str,
        module: str,
        file_path: str,
        recv_type: str,
        fun_name: str,
        reconciler_type: str,
    ):
        self.__id = int(id)
        self.__module = module
        self.__file_path = file_path
        self.__recv_type = recv_type
        self.__fun_name = fun_name
        self.__reconciler_type = reconciler_type
        self.__reconcile_id = -1
        self.__start_timestamp = -1
        self.__end_timestamp = -1
        self.__range_start_timestamp = -1
        self.__range_end_timestamp = -1
        self.__signature_counter = 1

    @property
    def id(self):
        return self.__id

    @property
    def module(self):
        return self.__module

    @property
    def file_path(self):
        return self.__file_path

    @property
    def recv_type(self):
        return self.__recv_type

    @property
    def fun_name(self):
        return self.__fun_name

    @property
    def reconciler_type(self):
        return self.__reconciler_type

    @property
    def reconcile_id(self):
        return self.__reconcile_id

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
    def signature_counter(self):
        return self.__signature_counter

    @reconciler_type.setter
    def reconciler_type(self, reconciler_type: str):
        self.__reconciler_type = reconciler_type

    @reconcile_id.setter
    def reconcile_id(self, reconcile_id: int):
        self.__reconcile_id = reconcile_id

    @start_timestamp.setter
    def start_timestamp(self, start_timestamp: int):
        self.__start_timestamp = start_timestamp

    @end_timestamp.setter
    def end_timestamp(self, end_timestamp: int):
        self.__end_timestamp = end_timestamp

    @range_start_timestamp.setter
    def range_start_timestamp(self, range_start_timestamp: int):
        self.__range_start_timestamp = range_start_timestamp

    @range_end_timestamp.setter
    def range_end_timestamp(self, range_end_timestamp: int):
        self.__range_end_timestamp = range_end_timestamp

    @signature_counter.setter
    def signature_counter(self, signature_counter: int):
        self.__signature_counter = signature_counter


class OperatorWrite:
    def __init__(
        self,
        id: str,
        etype: str,
        reconciler_type: str,
        error: str,
        rtype: str,
        namespace: str,
        name: str,
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
        self.__namespace = namespace
        self.__name = name if name != "" else extract_name(self.obj_map)
        self.__start_timestamp = -1
        self.__end_timestamp = -1
        self.__range_start_timestamp = -1
        self.__range_end_timestamp = -1
        self.__read_types = set()
        self.__read_keys = set()
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

    @reconciler_type.setter
    def reconciler_type(self, reconciler_type: str):
        self.__reconciler_type = reconciler_type

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
            if objs is not None:
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


class OperatorNonK8sWriteIDOnly:
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
    assert SIEVE_AFTER_REST_WRITE_MARK in line
    tokens = line[line.find(SIEVE_AFTER_REST_WRITE_MARK) :].strip("\n").split("\t")
    return OperatorWrite(
        tokens[1],
        tokens[2],
        tokens[3],
        tokens[4],
        tokens[5],
        tokens[6],
        tokens[7],
        tokens[8],
    )


def parse_operator_non_k8s_write(line: str) -> OperatorNonK8sWrite:
    assert SIEVE_AFTER_ANNOTATED_API_INVOCATION_MARK in line
    tokens = (
        line[line.find(SIEVE_AFTER_ANNOTATED_API_INVOCATION_MARK) :]
        .strip("\n")
        .split("\t")
    )
    return OperatorNonK8sWrite(
        tokens[1], tokens[2], tokens[3], tokens[4], tokens[5], tokens[6]
    )


def parse_operator_read(line: str) -> OperatorRead:
    assert SIEVE_AFTER_CACHE_READ_MARK in line
    tokens = line[line.find(SIEVE_AFTER_CACHE_READ_MARK) :].strip("\n").split("\t")
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
    assert SIEVE_AFTER_REST_WRITE_MARK in line or SIEVE_BEFORE_REST_WRITE_MARK in line
    if SIEVE_AFTER_REST_WRITE_MARK in line:
        tokens = line[line.find(SIEVE_AFTER_REST_WRITE_MARK) :].strip("\n").split("\t")
        return OperatorWriteIDOnly(tokens[1])
    else:
        tokens = line[line.find(SIEVE_BEFORE_REST_WRITE_MARK) :].strip("\n").split("\t")
        return OperatorWriteIDOnly(tokens[1])


def parse_operator_non_k8s_write_id_only(line: str) -> OperatorNonK8sWriteIDOnly:
    assert (
        SIEVE_AFTER_ANNOTATED_API_INVOCATION_MARK in line
        or SIEVE_BEFORE_ANNOTATED_API_INVOCATION_MARK in line
    )
    if SIEVE_AFTER_ANNOTATED_API_INVOCATION_MARK in line:
        tokens = (
            line[line.find(SIEVE_AFTER_ANNOTATED_API_INVOCATION_MARK) :]
            .strip("\n")
            .split("\t")
        )
        return OperatorNonK8sWriteIDOnly(tokens[1])
    else:
        tokens = (
            line[line.find(SIEVE_BEFORE_ANNOTATED_API_INVOCATION_MARK) :]
            .strip("\n")
            .split("\t")
        )
        return OperatorNonK8sWriteIDOnly(tokens[1])


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
    return APIEvent(tokens[1], tokens[2], tokens[3], tokens[4], tokens[5], tokens[6])


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
