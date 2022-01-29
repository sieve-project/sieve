import json
import os
from typing import Container

sieve_config = {
    "docker_repo": "ghcr.io/sieve-project/action",
    "namespace": "default",
    "stale_state_front_runner": "kind-control-plane",
    "stale_state_straggler": "kind-control-plane3",
    "k8s_event_check_list": ["DELETED", "ADDED"],
    "k8s_type_check_list": [
        "pod",
        "deployment",
        "statefulset",
        "persistentvolumeclaim",
        "secret",
        "service",
        "replicaset",
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
    "stale_state_spec_generation_delete_only": True,
    "stale_state_spec_generation_causality_pass_enabled": True,
    "stale_state_spec_generation_reversed_pass_enabled": True,
    "unobserved_state_spec_generation_causality_pass_enabled": True,
    "unobserved_state_spec_generation_overwrite_pass_enabled": True,
    "intermediate_state_spec_generation_error_free_pass_enabled": True,
    "persist_specs_enabled": True,
    "remove_nondeterministic_key_enabled": True,
    "update_cancels_delete_enabled": True,
}

if os.path.isfile("sieve_config.json"):
    json_config = json.loads(open("sieve_config.json").read())
    for key in json_config:
        sieve_config[key] = json_config[key]
    if not sieve_config["liveness_checker_enabled"]:
        sieve_config["compare_states_checker_enabled"] = False
    if not sieve_config["safety_checker_enabled"]:
        sieve_config["compare_history_digests_checker_enabled"] = False


class ControllerConfig:
    def __init__(
        self,
        controller_name,
        github_link,
        commit,
        kubernetes_version,
        controller_runtime_version,
        client_go_version,
        application_dir,
        docker_file_path,
        test_command,
        custom_resource_definitions,
        deployment_name,
        controller_pod_label,
        container_name,
        controller_deployment_file_path,
        test_setting,
        end_state_checker_mask,
        state_update_summary_checker_mask,
    ):
        self.controller_name = controller_name
        self.github_link = github_link
        self.commit = commit
        self.kubernetes_version = kubernetes_version
        self.controller_runtime_version = controller_runtime_version
        self.client_go_version = client_go_version
        self.application_dir = application_dir
        self.docker_file_path = docker_file_path
        self.test_command = test_command
        self.custom_resource_definitions = custom_resource_definitions
        self.deployment_name = deployment_name
        self.controller_pod_label = controller_pod_label
        self.container_name = container_name
        self.controller_deployment_file_path = controller_deployment_file_path
        self.test_setting = test_setting
        self.end_state_checker_mask = end_state_checker_mask
        self.state_update_summary_checker_mask = state_update_summary_checker_mask


def get_global_config():
    return sieve_config


def get_controller_config(controller_name):
    controller_config_path = os.path.join("examples", controller_name, "config.json")
    controller_config = json.load(open(controller_config_path))
    return ControllerConfig(
        controller_name=controller_name,
        github_link=controller_config["github_link"],
        commit=controller_config["commit"],
        kubernetes_version=controller_config["kubernetes_version"],
        controller_runtime_version=controller_config["controller_runtime_version"],
        client_go_version=controller_config["client_go_version"],
        application_dir=controller_config["application_dir"],
        docker_file_path=controller_config["docker_file_path"],
        test_command=controller_config["test_command"],
        custom_resource_definitions=controller_config["custom_resource_definitions"],
        deployment_name=controller_config["deployment_name"],
        controller_pod_label=controller_config["controller_pod_label"],
        container_name=controller_config["container_name"]
        if "container_name" in controller_config
        else None,
        controller_deployment_file_path=controller_config[
            "controller_deployment_file_path"
        ],
        test_setting=controller_config["test_setting"]
        if "test_setting" in controller_config
        else {},
        end_state_checker_mask=controller_config["end_state_checker_mask"]
        if "end_state_checker_mask" in controller_config
        else {},
        state_update_summary_checker_mask=controller_config[
            "state_update_summary_checker_mask"
        ]
        if "state_update_summary_checker_mask" in controller_config
        else {},
    )
