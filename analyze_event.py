import common
import copy


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


def compress_event_object(prev_object, cur_object, slim_prev_object, slim_cur_object):
    to_del = []
    to_del_cur = []
    to_del_prev = []
    allKeys = set(cur_object.keys()).union(prev_object.keys())
    for key in allKeys:
        if key not in cur_object:
            continue
        elif key not in prev_object:
            continue
        elif key in common.BORING_EVENT_OBJECT_FIELDS:
            to_del.append(key)
        elif str(cur_object[key]) != str(prev_object[key]):
            if isinstance(cur_object[key], dict):
                if not isinstance(prev_object[key], dict):
                    continue
                res = compress_event_object(
                    prev_object[key], cur_object[key], slim_prev_object[key], slim_cur_object[key])
                if res:
                    to_del.append(key)
            elif isinstance(cur_object[key], list):
                if not isinstance(prev_object[key], list):
                    continue
                for i in range(len(cur_object[key])):
                    if i >= len(prev_object[key]):
                        break
                    elif str(cur_object[key][i]) != str(prev_object[key][i]):
                        if isinstance(cur_object[key][i], dict):
                            if not isinstance(prev_object[key][i], dict):
                                continue
                            res = compress_event_object(
                                prev_object[key][i], cur_object[key][i], slim_prev_object[key][i], slim_cur_object[key][i])
                            if res:
                                # SONAR_SKIP means we can skip the value in list when later comparing to the events in testing run
                                slim_cur_object[key][i] = common.SONAR_SKIP_MARKER
                                slim_prev_object[key][i] = common.SONAR_SKIP_MARKER
                        elif isinstance(cur_object[key][i], list):
                            # TODO: we need to consider list in list
                            assert False
                        else:
                            continue
                    else:
                        slim_cur_object[key][i] = common.SONAR_SKIP_MARKER
                        slim_prev_object[key][i] = common.SONAR_SKIP_MARKER
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


def canonicalize_event(event):
    for key in event:
        if isinstance(event[key], dict):
            canonicalize_event(event[key])
        else:
            # TODO: we should check value and see if it is time format
            if "time" in key.lower():
                event[key] = common.SONAR_CANONICALIZATION_MARKER
    return event
