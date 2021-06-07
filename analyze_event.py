import common
import copy
import re


def find_previous_event(event, event_map):
    id = event.id
    key = event.key
    assert key in event_map, "invalid key %s, not found in event_map" % (key)
    for i in range(len(event_map[key])):
        if event_map[key][i].id == id:
            if i == 0:
                return None, event_map[key][i]
            else:
                return event_map[key][i-1], event_map[key][i]


def compress_event_object_for_list(prev_object, cur_object, slim_prev_object, slim_cur_object):
    for i in range(min(len(cur_object), len(prev_object))):
        if str(cur_object[i]) != str(prev_object[i]):
            if isinstance(cur_object[i], dict):
                if not isinstance(prev_object[i], dict):
                    continue
                if compress_event_object(
                        prev_object[i], cur_object[i], slim_prev_object[i], slim_cur_object[i]):
                    # SONAR_SKIP means we can skip the value in list when later comparing to the events in testing run
                    slim_cur_object[i] = common.SONAR_SKIP_MARKER
                    slim_prev_object[i] = common.SONAR_SKIP_MARKER
            elif isinstance(cur_object[i], list):
                if not isinstance(prev_object[i], list):
                    continue
                if compress_event_object_for_list(
                        prev_object[i], cur_object[i], slim_prev_object[i], slim_cur_object[i]):
                    slim_cur_object[i] = common.SONAR_SKIP_MARKER
                    slim_prev_object[i] = common.SONAR_SKIP_MARKER
            else:
                continue
        else:
            slim_cur_object[i] = common.SONAR_SKIP_MARKER
            slim_prev_object[i] = common.SONAR_SKIP_MARKER

    if len(slim_cur_object) != len(slim_prev_object):
        return False
    for i in range(len(slim_cur_object)):
        if slim_cur_object[i] != common.SONAR_SKIP_MARKER:
            return False
    return True


def compress_event_object(prev_object, cur_object, slim_prev_object, slim_cur_object):
    to_del = []
    to_del_cur = []
    to_del_prev = []
    common_keys = set(cur_object.keys()).intersection(prev_object.keys())
    for key in common_keys:
        if key in common.BORING_EVENT_OBJECT_FIELDS:
            to_del.append(key)
        elif str(cur_object[key]) != str(prev_object[key]):
            if isinstance(cur_object[key], dict):
                if not isinstance(prev_object[key], dict):
                    continue
                if compress_event_object(
                        prev_object[key], cur_object[key], slim_prev_object[key], slim_cur_object[key]):
                    to_del.append(key)
            elif isinstance(cur_object[key], list):
                if not isinstance(prev_object[key], list):
                    continue
                if compress_event_object_for_list(
                        prev_object[key], cur_object[key], slim_prev_object[key], slim_cur_object[key]):
                    to_del.append(key)
            else:
                continue
        else:
            to_del.append(key)
    for key in to_del:
        del slim_cur_object[key]
        del slim_prev_object[key]
    for key in slim_cur_object:
        if isinstance(slim_cur_object[key], dict):
            if len(slim_cur_object[key]) == 0:
                to_del_cur.append(key)
    for key in slim_prev_object:
        if isinstance(slim_prev_object[key], dict):
            if len(slim_prev_object[key]) == 0:
                to_del_prev.append(key)
    for key in to_del_cur:
        del slim_cur_object[key]
    for key in to_del_prev:
        del slim_prev_object[key]
    if len(slim_cur_object) == 0 and len(slim_prev_object) == 0:
        return True
    return False


def diff_events(prev_event, cur_event):
    prev_object = prev_event.obj
    cur_object = cur_event.obj
    slim_prev_object = copy.deepcopy(prev_object)
    slim_cur_object = copy.deepcopy(cur_object)
    compress_event_object(prev_object, cur_object,
                          slim_prev_object, slim_cur_object)
    return slim_prev_object, slim_cur_object


def canonicalize_event_for_list(event_list, node_ignore):
    for i in range(len(event_list)):
        if isinstance(event_list[i], list):
            canonicalize_event_for_list(event_list[i], node_ignore)
        elif isinstance(event_list[i], dict):
            canonicalize_event(event_list[i], node_ignore)
        elif isinstance(event_list[i], str):
            if re.match(common.TIME_REG, str(event_list[i])):
                event_list[i] = common.SONAR_CANONICALIZATION_MARKER
    return event_list


def canonicalize_event(event, node_ignore):
    for key in event:
        if isinstance(event[key], dict):
            canonicalize_event(event[key], node_ignore)
        elif isinstance(event[key], list):
            canonicalize_event_for_list(event[key], node_ignore)
        elif isinstance(event[key], str):
            if re.match(common.TIME_REG, str(event[key])):
                event[key] = common.SONAR_CANONICALIZATION_MARKER
            if node_ignore:
                if 'ip' in key.lower() and re.match(common.IP_REG, str(event[key])):
                    event[key] = common.SONAR_CANONICALIZATION_MARKER
                if key in common.PLACEHOLDER_FIELDS:
                    event[key] = common.SONAR_CANONICALIZATION_MARKER
    return event
