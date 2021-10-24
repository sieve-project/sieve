import json
import os

config = {
    "docker_repo": "ghcr.io/sieve-project/action",
    "namespace": "default",
    "time_travel_front_runner": "kind-control-plane",
    "time_travel_straggler": "kind-control-plane3",
    "api_event_to_check": ["DELETED", "ADDED"],
    "compress_trivial_reconcile": True,
    "workload_wait_soft_timeout": 100,
    "workload_wait_hard_timeout": 600,
    "generic_event_generation_enabled": True,
    "generic_state_generation_enabled": True,
    "generic_event_checker_enabled": True,
    "generic_type_event_checker_enabled": False,
    "generic_state_checker_enabled": True,
    "operator_checker_enabled": True,
    "test_workload_checker_enabled": True,
    "injection_desc_generation_enabled": True,
}

if os.path.isfile("sieve_config.json"):
    json_config = json.loads(open("sieve_config.json").read())
    for key in json_config:
        config[key] = json_config[key]
    if not config["generic_state_generation_enabled"]:
        config["generic_state_checker_enabled"] = False
