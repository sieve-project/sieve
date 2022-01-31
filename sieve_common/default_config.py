import json
import os


class CommonConfig:
    def __init__(
        self,
        docker_registry,
        namespace,
        leading_api,
        following_api,
        state_update_summary_check_enabled,
        end_state_check_enabled,
        workload_error_check_enabled,
        controller_exception_check_enabled,
        state_update_summary_check_event_list,
        end_state_resource_check_list,
        compress_trivial_reconcile_enabled,
        workload_hard_timeout,
        workload_soft_timeout,
        generate_debugging_information_enabled,
        causality_prunning_enabled,
        effective_updates_pruning_enabled,
        nondeterministic_pruning_enabled,
        persist_test_plans_enabled,
    ):
        self.docker_registry = docker_registry
        self.namespace = namespace
        self.leading_api = leading_api
        self.following_api = following_api
        self.state_update_summary_check_enabled = state_update_summary_check_enabled
        self.end_state_check_enabled = end_state_check_enabled
        self.workload_error_check_enabled = workload_error_check_enabled
        self.controller_exception_check_enabled = controller_exception_check_enabled
        self.state_update_summary_check_event_list = (
            state_update_summary_check_event_list
        )
        self.end_state_resource_check_list = end_state_resource_check_list
        self.compress_trivial_reconcile_enabled = compress_trivial_reconcile_enabled
        self.workload_hard_timeout = workload_hard_timeout
        self.workload_soft_timeout = workload_soft_timeout
        self.generate_debugging_information_enabled = (
            generate_debugging_information_enabled
        )
        self.causality_prunning_enabled = causality_prunning_enabled
        self.effective_updates_pruning_enabled = effective_updates_pruning_enabled
        self.nondeterministic_pruning_enabled = nondeterministic_pruning_enabled
        self.persist_test_plans_enabled = persist_test_plans_enabled


def get_common_config():
    common_config_path = "default_config.json"
    common_config = json.load(open(common_config_path))
    if os.path.isfile("sieve_config.json"):
        override_config = json.loads(open("sieve_config.json").read())
        for key in override_config:
            common_config[key] = override_config[key]
    return CommonConfig(
        docker_registry=common_config["docker_registry"],
        namespace=common_config["namespace"],
        leading_api=common_config["leading_api"],
        following_api=common_config["following_api"],
        state_update_summary_check_enabled=common_config[
            "state_update_summary_check_enabled"
        ],
        end_state_check_enabled=common_config["end_state_check_enabled"],
        workload_error_check_enabled=common_config["workload_error_check_enabled"],
        controller_exception_check_enabled=common_config[
            "controller_exception_check_enabled"
        ],
        state_update_summary_check_event_list=common_config[
            "state_update_summary_check_event_list"
        ],
        end_state_resource_check_list=common_config["end_state_resource_check_list"],
        compress_trivial_reconcile_enabled=common_config[
            "compress_trivial_reconcile_enabled"
        ],
        workload_hard_timeout=common_config["workload_hard_timeout"],
        workload_soft_timeout=common_config["workload_soft_timeout"],
        generate_debugging_information_enabled=[
            "generate_debugging_information_enabled"
        ],
        causality_prunning_enabled=common_config["causality_prunning_enabled"],
        effective_updates_pruning_enabled=common_config[
            "effective_updates_pruning_enabled"
        ],
        nondeterministic_pruning_enabled=common_config[
            "nondeterministic_pruning_enabled"
        ],
        persist_test_plans_enabled=common_config["persist_test_plans_enabled"],
    )


class ControllerConfig:
    def __init__(
        self,
        controller_name,
        github_link,
        commit,
        cherry_pick_commits,
        kubernetes_version,
        controller_runtime_version,
        client_go_version,
        apimachinery_version,
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
        self.cherry_pick_commits = cherry_pick_commits
        self.kubernetes_version = kubernetes_version
        self.controller_runtime_version = controller_runtime_version
        self.client_go_version = client_go_version
        self.apimachinery_version = apimachinery_version
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


def get_controller_config(controller_name):
    controller_config_path = os.path.join("examples", controller_name, "config.json")
    controller_config = json.load(open(controller_config_path))
    return ControllerConfig(
        controller_name=controller_name,
        github_link=controller_config["github_link"],
        commit=controller_config["commit"],
        cherry_pick_commits=controller_config["cherry_pick_commits"]
        if "cherry_pick_commits" in controller_config
        else [],
        kubernetes_version=controller_config["kubernetes_version"],
        controller_runtime_version=controller_config["controller_runtime_version"],
        client_go_version=controller_config["client_go_version"],
        apimachinery_version=controller_config["apimachinery_version"]
        if "apimachinery_version" in controller_config
        else None,
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
