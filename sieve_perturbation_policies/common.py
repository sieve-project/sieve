import json
import os
from sieve_common.event_delta import *
from sieve_common.common import *
from sieve_common.k8s_event import *


def convert_deltafifo_etype_to_API_etype(etype: str) -> str:
    if etype == ControllerHearTypes.ADDED:
        return APIEventTypes.ADDED
    elif etype == ControllerHearTypes.UPDATED:
        return APIEventTypes.MODIFIED
    elif etype == ControllerHearTypes.DELETED:
        return APIEventTypes.DELETED
    else:
        return APIEventTypes.MODIFIED


def event_diff_validation_check(prev_etype: str, cur_etype: str):
    if prev_etype == cur_etype and (
        prev_etype == ControllerHearTypes.ADDED
        or prev_etype == ControllerHearTypes.DELETED
    ):
        # this should never happen
        assert False, "There should not be consecutive Deleted | Added"
    if (
        prev_etype == ControllerHearTypes.DELETED
        and cur_etype != ControllerHearTypes.ADDED
        and cur_etype != ControllerHearTypes.UPDATED
    ):
        # this should never happen
        assert False, "Deleted must be followed with Added | Updated"
    if (
        prev_etype != EVENT_NONE_TYPE
        and prev_etype != ControllerHearTypes.DELETED
        and cur_etype == ControllerHearTypes.ADDED
    ):
        # this should never happen
        assert False, "Added must be the first or follow Deleted"


def detectable_event_diff(
    recv_event: bool,
    diff_prev_obj: Optional[Dict],
    diff_cur_obj: Optional[Dict],
    prev_etype: str,
    cur_etype: str,
    signature_counter: int,
) -> bool:
    if signature_counter > 3:
        return False
    if recv_event:
        event_diff_validation_check(prev_etype, cur_etype)
        # undetectable if the first event is not ADDED
        if prev_etype == EVENT_NONE_TYPE and cur_etype != ControllerHearTypes.ADDED:
            return False
        # undetectable if not in detectable_controller_hear_types
        if cur_etype not in detectable_controller_hear_types:
            return False
        # undetectable if nothing changed after update
        elif diff_prev_obj == diff_cur_obj and cur_etype == ControllerHearTypes.UPDATED:
            return False
        else:
            return True
    else:
        # undetectable if not in detectable_controller_write_types
        if cur_etype not in detectable_controller_write_types:
            return False
        # undetectable if nothing changed after update or patch
        elif diff_prev_obj == diff_cur_obj and (
            cur_etype == ControllerWriteTypes.UPDATE
            or cur_etype == ControllerWriteTypes.PATCH
            or cur_etype == ControllerWriteTypes.STATUS_UPDATE
            or cur_etype == ControllerWriteTypes.STATUS_PATCH
        ):
            return False
        # undetectable if status update/patch does not modify status
        elif (
            diff_prev_obj is not None
            and "status" not in diff_prev_obj
            and diff_cur_obj is not None
            and "status" not in diff_cur_obj
            and (
                cur_etype == ControllerWriteTypes.STATUS_UPDATE
                or cur_etype == ControllerWriteTypes.STATUS_PATCH
            )
        ):
            return False
        else:
            return True


def nondeterministic_key(
    test_context: TestContext, event: Union[ControllerHear, ControllerWrite]
):
    generate_name = extract_generate_name(event.obj_map)
    end_state = json.load(
        open(
            os.path.join(
                test_context.oracle_dir,
                "state.json",
            )
        )
    )
    if event.key not in end_state:
        # TODO: get rid of the heuristic
        if generate_name is not None and is_generated_random_name(
            event.name, generate_name
        ):
            return True
    elif end_state[event.key] == "SIEVE-IGNORE":
        return True
    return False
