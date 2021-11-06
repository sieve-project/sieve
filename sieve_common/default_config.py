import json
import os

sieve_config = {
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
    "compare_history_digests_checker_enabled": True,
    "generic_type_event_checker_enabled": False,
    "compare_states_checker_enabled": True,
    "operator_panic_checker_enabled": True,
    "test_failure_checker_enabled": True,
    "injection_desc_generation_enabled": True,
    "time_travel_spec_generation_delete_only_pass_enabled": True,
    "obs_gap_spec_generation_conflicting_follower_enabled": True,
    "atom_vio_spec_generation_error_free_pass_enabled": True,
}

if os.path.isfile("sieve_config.json"):
    json_config = json.loads(open("sieve_config.json").read())
    for key in json_config:
        sieve_config[key] = json_config[key]
    if not sieve_config["generic_state_generation_enabled"]:
        sieve_config["compare_states_checker_enabled"] = False
