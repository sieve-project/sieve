import json
import os

sieve_config = {
    "docker_repo": "ghcr.io/sieve-project/action",
    "namespace": "default",
    "time_travel_front_runner": "kind-control-plane",
    "time_travel_straggler": "kind-control-plane3",
    "k8s_event_check_list": ["DELETED", "ADDED"],
    "k8s_type_check_list": [
        "pod",
        "deployment",
        "statefulset",
        "persistentvolumeclaim",
        "secret",
        "service",
    ],
    "compress_trivial_reconcile": True,
    "workload_wait_soft_timeout": 100,
    "workload_wait_hard_timeout": 600,
    "safety_checker_enabled": True,
    "liveness_checker_enabled": True,
    "compare_history_digests_checker_enabled": True,
    "compare_states_checker_enabled": True,
    "operator_panic_checker_enabled": True,
    "test_failure_checker_enabled": True,
    "test_workload_checker_enabled": True,
    "injection_desc_generation_enabled": True,
    "spec_generation_detectable_pass_enabled": True,
    "spec_generation_causal_info_pass_enabled": True,
    "spec_generation_type_specific_pass_enabled": True,
    "time_travel_spec_generation_delete_only": True,
    "time_travel_spec_generation_causality_pass_enabled": True,
    "time_travel_spec_generation_reversed_pass_enabled": True,
    "obs_gap_spec_generation_causality_pass_enabled": True,
    "obs_gap_spec_generation_overwrite_pass_enabled": True,
    "atom_vio_spec_generation_error_free_pass_enabled": True,
    "persist_specs_enabled": True,
    "remove_nondeterministic_key_enabled": True,
}

if os.path.isfile("sieve_config.json"):
    json_config = json.loads(open("sieve_config.json").read())
    for key in json_config:
        sieve_config[key] = json_config[key]
    if not sieve_config["liveness_checker_enabled"]:
        sieve_config["compare_states_checker_enabled"] = False
    if not sieve_config["safety_checker_enabled"]:
        sieve_config["compare_history_digests_checker_enabled"] = False
