import json
import os

config = {
    "docker_repo": "xudongs",
    "namespace": "default",
    "time_travel_front_runner": "kind-control-plane",
    "time_travel_straggler": "kind-control-plane3",
    "effect_to_check": ["Delete"],
    "compress_trivial_reconcile": True,
    "workload_wait_timeout": 600
}

if os.path.isfile("sieve_config.json"):
    json_config = json.loads(open("sieve_config.json").read())
    for key in json_config:
        config[key] = json_config[key]
