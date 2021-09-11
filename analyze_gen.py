import json
import yaml
import copy
import os
import controllers
import analyze_event
import json
import sieve_config
from common import sieve_modes


def time_travel_description(yaml_map):
    return "Pause %s after it processes a %s event E. "\
        "E should match the pattern %s and the events before E should match %s. "\
        "And restart the controller %s after %s processes a %s %s event." % (
            yaml_map["straggler"], "/".join([yaml_map["ce-namespace"],
                                             yaml_map["ce-rtype"], yaml_map["ce-name"]]),
            yaml_map["ce-diff-current"], yaml_map["ce-diff-previous"], yaml_map["operator-pod-label"],
            yaml_map["front-runner"], yaml_map["se-etype"], "/".join([yaml_map["se-namespace"],
                                                                      yaml_map["se-rtype"], yaml_map["se-name"]]))


def obs_gap_description(yaml_map):
    return "Pause any reconcile on %s after it sees a %s event E. "\
        "E should match the pattern %s and the events before E should match %s. "\
        "And resume reconcile on the controller %s after it sees an event cancel event E." % (
            yaml_map["operator-pod-label"], "/".join([yaml_map["ce-namespace"],
                                                      yaml_map["ce-rtype"], yaml_map["ce-name"]]),
            yaml_map["ce-diff-current"], yaml_map["ce-diff-previous"], yaml_map["operator-pod-label"],
        )


def generate_time_travel_yaml(triggering_points, path, project, timing="after"):
    yaml_map = {}
    yaml_map["project"] = project
    yaml_map["stage"] = "test"
    yaml_map["mode"] = sieve_modes.TIME_TRAVEL
    yaml_map["straggler"] = sieve_config.config["time_travel_straggler"]
    yaml_map["front-runner"] = sieve_config.config["time_travel_front_runner"]
    yaml_map["operator-pod-label"] = controllers.operator_pod_label[project]
    yaml_map["deployment-name"] = controllers.deployment_name[project]
    yaml_map["timing"] = timing
    suffix = "-b" if timing == "before" else ""
    i = 0
    for triggering_point in triggering_points:
        assert triggering_point["ttype"] == "event-delta"
        i += 1
        effect = triggering_point["effect"]
        yaml_map["ce-name"] = triggering_point["name"]
        yaml_map["ce-namespace"] = triggering_point["namespace"]
        yaml_map["ce-rtype"] = triggering_point["rtype"]
        yaml_map["ce-diff-current"] = json.dumps(
            analyze_event.canonicalize_event(copy.deepcopy(triggering_point["curEvent"])))
        yaml_map["ce-diff-previous"] = json.dumps(
            analyze_event.canonicalize_event(copy.deepcopy(triggering_point["prevEvent"])))
        yaml_map["ce-etype-current"] = triggering_point["curEventType"]
        yaml_map["ce-etype-previous"] = triggering_point["prevEventType"]
        yaml_map["se-name"] = effect["name"]
        yaml_map["se-namespace"] = effect["namespace"]
        yaml_map["se-rtype"] = effect["rtype"]
        yaml_map["se-etype"] = "ADDED" if effect["etype"] == "Delete" else "DELETED"
        yaml_map["description"] = time_travel_description(yaml_map)
        yaml.dump(yaml_map, open(
            os.path.join(path, "time-travel-config-%s%s.yaml" % (str(i), suffix)), "w"), sort_keys=False)
    print("Generated %d time-travel config(s) in %s" % (i, path))


def generate_obs_gap_yaml(triggering_points, path, project):
    yaml_map = {}
    yaml_map["project"] = project
    yaml_map["stage"] = "test"
    yaml_map["mode"] = sieve_modes.OBS_GAP
    yaml_map["operator-pod-label"] = controllers.operator_pod_label[project]
    i = 0
    events_set = set()
    for triggering_point in triggering_points:
        if triggering_point["curEventId"] not in events_set:
            events_set.add(triggering_point["curEventId"])
        else:
            continue
        assert triggering_point["ttype"] == "event-delta"
        i += 1
        yaml_map["ce-name"] = triggering_point["name"]
        yaml_map["ce-namespace"] = triggering_point["namespace"]
        yaml_map["ce-rtype"] = triggering_point["rtype"]
        yaml_map["ce-diff-current"] = json.dumps(
            analyze_event.canonicalize_event(copy.deepcopy(triggering_point["curEvent"])))
        yaml_map["ce-diff-previous"] = json.dumps(
            analyze_event.canonicalize_event(copy.deepcopy(triggering_point["prevEvent"])))
        yaml_map["ce-etype-current"] = triggering_point["curEventType"]
        yaml_map["ce-etype-previous"] = triggering_point["prevEventType"]
        yaml_map["description"] = obs_gap_description(yaml_map)
        yaml.dump(yaml_map, open(
            os.path.join(path, "obs-gap-config-%s.yaml" % (str(i))), "w"), sort_keys=False)
    print("Generated %d obs-gap config(s) in %s" % (i, path))


def generate_atomic_yaml(triggering_points, path, project):
    yaml_map = {}
    yaml_map["project"] = project
    yaml_map["stage"] = "test"
    yaml_map["mode"] = sieve_modes.ATOM_VIO
    yaml_map["front-runner"] = sieve_config.config["time_travel_front_runner"]
    yaml_map["operator-pod-label"] = controllers.operator_pod_label[project]
    yaml_map["deployment-name"] = controllers.deployment_name[project]
    i = 0
    for triggering_point in triggering_points:
        if triggering_point["ttype"] != "event-delta":
            # TODO: handle the single event trigger
            continue
        i += 1
        effect = triggering_point["effect"]
        yaml_map["ce-name"] = triggering_point["name"]
        yaml_map["ce-namespace"] = triggering_point["namespace"]
        yaml_map["ce-rtype"] = triggering_point["rtype"]
        yaml_map["ce-diff-current"] = json.dumps(
            analyze_event.canonicalize_event(copy.deepcopy(triggering_point["curEvent"])))
        yaml_map["ce-diff-previous"] = json.dumps(
            analyze_event.canonicalize_event(copy.deepcopy(triggering_point["prevEvent"])))
        yaml_map["ce-etype-current"] = triggering_point["curEventType"]
        yaml_map["ce-etype-previous"] = triggering_point["prevEventType"]
        yaml_map["se-name"] = effect["name"]
        yaml_map["se-namespace"] = effect["namespace"]
        yaml_map["se-rtype"] = effect["rtype"]
        yaml_map["se-etype"] = effect["etype"]
        # TODO: should find a way to determine crash location
        yaml_map["crash-location"] = "before"
        yaml_map["description"] = ""
        yaml.dump(yaml_map, open(
            os.path.join(path, "atomic-config-%s.yaml" % (str(i))), "w"), sort_keys=False)
    print("Generated %d atomic config(s) in %s" % (i, path))
