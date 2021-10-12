import json
import os

config = {
    "docker_repo": "ghcr.io/sieve-project/action",
    "namespace": "default",
    "time_travel_front_runner": "kind-control-plane",
    "time_travel_straggler": "kind-control-plane3",
    "api_event_to_check": ["DELETED"],
    "compress_trivial_reconcile": True,
    "workload_wait_soft_timeout": 100,
    "workload_wait_hard_timeout": 600,
    "generate_status": True,
    "generate_events_oracle": True,
    "generate_resource": True,
    "check_status": True,
    "check_event_oracle": True,
    "check_resource": True,
    "check_operator_log": True,
    "check_workload_log": True,
    "generate_injection_desc": True,
}

if os.path.isfile("sieve_config.json"):
    json_config = json.loads(open("sieve_config.json").read())
    for key in json_config:
        config[key] = json_config[key]
    if not config["generate_status"]:
        config["check_status"] = False
    if not config["generate_resource"]:
        config["check_resource"] = False
