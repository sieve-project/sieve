import json
import os

config = {
    "docker_repo": "ghcr.io/sieve-project/action",
    "namespace": "default",
    "time_travel_front_runner": "kind-control-plane",
    "time_travel_straggler": "kind-control-plane3",
    "effect_to_check": ["Delete"],
    "compress_trivial_reconcile": True,
    "workload_wait_timeout": 600,
    "check_digest": True,
    "check_resource": True,
    "check_operator_log": True,
}

if os.path.isfile("sieve_config.json"):
    json_config = json.loads(open("sieve_config.json").read())
    for key in json_config:
        config[key] = json_config[key]
