import copy
import re
from typing import Dict, List, Tuple, Optional
from common import *


def diff_event_as_list(
    prev_event: List, cur_event: List
) -> Tuple[Optional[List], Optional[List]]:
    prev_len = len(prev_event)
    cur_len = len(cur_event)
    min_len = min(prev_len, cur_len)
    diff_prev_event = [SIEVE_SKIP_MARKER] * prev_len
    diff_cur_event = [SIEVE_SKIP_MARKER] * cur_len
    for i in range(min_len):
        if isinstance(cur_event[i], dict):
            if not isinstance(prev_event[i], dict):
                diff_prev_event[i] = prev_event[i]
                diff_cur_event[i] = cur_event[i]
            else:
                sub_diff_prev_event, sub_diff_cur_event = diff_event_as_map(
                    prev_event[i], cur_event[i]
                )
                if sub_diff_prev_event is None or sub_diff_cur_event is None:
                    continue
                diff_prev_event[i] = sub_diff_prev_event
                diff_cur_event[i] = sub_diff_cur_event
        elif isinstance(cur_event[i], list):
            if not isinstance(prev_event[i], list):
                diff_prev_event[i] = prev_event[i]
                diff_cur_event[i] = cur_event[i]
            else:
                sub_diff_prev_event, sub_diff_cur_event = diff_event_as_list(
                    prev_event[i], cur_event[i]
                )
                if sub_diff_prev_event is None or sub_diff_cur_event is None:
                    continue
                diff_prev_event[i] = sub_diff_prev_event
                diff_cur_event[i] = sub_diff_cur_event
        else:
            if prev_event[i] != cur_event[i]:
                diff_prev_event[i] = prev_event[i]
                diff_cur_event[i] = cur_event[i]
    if prev_len > min_len:
        for i in range(min_len, prev_len):
            diff_prev_event[i] = prev_event[i]
    if cur_len > min_len:
        for i in range(min_len, cur_len):
            diff_cur_event[i] = cur_event[i]
    if cur_len == prev_len:
        keep = False
        for i in range(cur_len):
            if (
                not diff_prev_event[i] == SIEVE_SKIP_MARKER
                or not diff_cur_event[i] == SIEVE_SKIP_MARKER
            ):
                keep = True
        if not keep:
            return None, None
    return diff_prev_event, diff_cur_event


def diff_event_as_map(
    prev_event: Dict, cur_event: Dict
) -> Tuple[Optional[Dict], Optional[Dict]]:
    diff_prev_event = {}
    diff_cur_event = {}

    common_keys = set(cur_event.keys()).intersection(prev_event.keys())
    pdc_keys = set(prev_event.keys()).difference(cur_event.keys())
    cdp_keys = set(cur_event.keys()).difference(prev_event.keys())
    for key in common_keys:
        if isinstance(cur_event[key], dict):
            if not isinstance(prev_event[key], dict):
                diff_prev_event[key] = prev_event[key]
                diff_cur_event[key] = cur_event[key]
            else:
                sub_diff_prev_event, sub_diff_cur_event = diff_event_as_map(
                    prev_event[key], cur_event[key]
                )
                if sub_diff_prev_event is None or sub_diff_cur_event is None:
                    continue
                diff_prev_event[key] = sub_diff_prev_event
                diff_cur_event[key] = sub_diff_cur_event
        elif isinstance(cur_event[key], list):
            if not isinstance(prev_event[key], list):
                diff_prev_event[key] = prev_event[key]
                diff_cur_event[key] = cur_event[key]
            else:
                sub_diff_prev_event, sub_diff_cur_event = diff_event_as_list(
                    prev_event[key], cur_event[key]
                )
                if sub_diff_prev_event is None or sub_diff_cur_event is None:
                    continue
                diff_prev_event[key] = sub_diff_prev_event
                diff_cur_event[key] = sub_diff_cur_event
        else:
            if prev_event[key] != cur_event[key]:
                diff_prev_event[key] = prev_event[key]
                diff_cur_event[key] = cur_event[key]
    for key in pdc_keys:
        diff_prev_event[key] = prev_event[key]
    for key in cdp_keys:
        diff_cur_event[key] = cur_event[key]
    if len(diff_cur_event) == 0 and len(diff_prev_event) == 0:
        return None, None
    return diff_prev_event, diff_cur_event


def canonicalize_value(value: str):
    if re.match(TIME_REG, value):
        return SIEVE_CANONICALIZATION_MARKER
    else:
        return value


def canonicalize_event_as_list(event: List):
    for i in range(len(event)):
        if isinstance(event[i], list):
            canonicalize_event_as_list(event[i])
        elif isinstance(event[i], dict):
            canonicalize_event_as_map(event[i])
        elif isinstance(event[i], str):
            event[i] = canonicalize_value(event[i])
    return event


def canonicalize_event_as_map(event: Dict):
    for key in event:
        if key in BORING_EVENT_OBJECT_FIELDS:
            event[key] = SIEVE_CANONICALIZATION_MARKER
            continue
        if isinstance(event[key], dict):
            canonicalize_event_as_map(event[key])
        elif isinstance(event[key], list):
            canonicalize_event_as_list(event[key])
        elif isinstance(event[key], str):
            event[key] = canonicalize_value(event[key])
    return event


def diff_event(
    prev_event: Dict, cur_event: Dict, trim_ka=False
) -> Tuple[Optional[Dict], Optional[Dict]]:
    prev_event_copy = copy.deepcopy(prev_event)
    cur_event_copy = copy.deepcopy(cur_event)
    if trim_ka:
        trim_kind_apiversion(prev_event_copy),
        trim_kind_apiversion(cur_event_copy),
    canonicalize_event_as_map(prev_event_copy)
    canonicalize_event_as_map(cur_event_copy)
    diff_prev_event, diff_cur_event = diff_event_as_map(prev_event_copy, cur_event_copy)
    return diff_prev_event, diff_cur_event


def cancel_event_obj_for_list(cur_object: List, following_object: List):
    if len(following_object) != len(cur_object):
        return True
    for i in range(len(cur_object)):
        if str(following_object[i]) != str(cur_object[i]):
            if isinstance(cur_object[i], dict):
                if not isinstance(following_object[i], dict):
                    return True
                elif cancel_event_object(cur_object[i], following_object[i]):
                    return True
            elif isinstance(cur_object[i], list):
                if not isinstance(following_object[i], list):
                    return True
                elif cancel_event_obj_for_list(cur_object[i], following_object[i]):
                    return True
            else:
                if (
                    cur_object[i] != SIEVE_CANONICALIZATION_MARKER
                    and cur_object[i] != SIEVE_SKIP_MARKER
                ):
                    return True
    return False


def cancel_event_object(cur_object: Dict, following_object: Dict):
    for key in cur_object:
        if key not in following_object:
            return True
        elif str(following_object[key]) != str(cur_object[key]):
            if isinstance(cur_object[key], dict):
                if not isinstance(following_object[key], dict):
                    return True
                elif cancel_event_object(cur_object[key], following_object[key]):
                    return True
            elif isinstance(cur_object[key], list):
                if not isinstance(following_object[key], list):
                    return True
                elif cancel_event_obj_for_list(cur_object[key], following_object[key]):
                    return True
            else:
                if cur_object[key] != SIEVE_CANONICALIZATION_MARKER:
                    return True
    return False


def trim_kind_apiversion(event: Dict):
    event.pop("kind", None)
    event.pop("apiVersion", None)
