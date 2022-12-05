import json
import os


class CommonConfig:
    def __init__(
        self,
        container_registry,
        namespace,
        leading_api,
        following_api,
        state_update_summary_check_enabled,
        end_state_check_enabled,
        workload_error_check_enabled,
        controller_exception_check_enabled,
        state_update_summary_check_event_list,
        compress_trivial_reconcile_enabled,
        workload_conditional_wait_timeout,
        workload_command_wait_timeout,
        generate_debugging_information_enabled,
        causality_pruning_enabled,
        effective_updates_pruning_enabled,
        nondeterministic_pruning_enabled,
        persist_test_plans_enabled,
        field_key_mask,
        field_path_mask,
        state_update_summary_checker_mask,
        update_oracle_file_enabled,
    ):
        self.container_registry = container_registry
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
        self.compress_trivial_reconcile_enabled = compress_trivial_reconcile_enabled
        self.workload_conditional_wait_timeout = workload_conditional_wait_timeout
        self.workload_command_wait_timeout = workload_command_wait_timeout
        self.generate_debugging_information_enabled = (
            generate_debugging_information_enabled
        )
        self.causality_pruning_enabled = causality_pruning_enabled
        self.effective_updates_pruning_enabled = effective_updates_pruning_enabled
        self.nondeterministic_pruning_enabled = nondeterministic_pruning_enabled
        self.persist_test_plans_enabled = persist_test_plans_enabled
        self.field_key_mask = field_key_mask
        self.field_path_mask = field_path_mask
        self.state_update_summary_checker_mask = state_update_summary_checker_mask
        self.update_oracle_file_enabled = update_oracle_file_enabled


def get_common_config():
    common_config_path = "config.json"
    common_config = json.load(open(common_config_path))
    if os.path.isfile("sieve_config.json"):
        override_config = json.loads(open("sieve_config.json").read())
        for key in override_config:
            common_config[key] = override_config[key]
    return CommonConfig(
        container_registry=common_config["container_registry"],
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
        compress_trivial_reconcile_enabled=common_config[
            "compress_trivial_reconcile_enabled"
        ],
        workload_conditional_wait_timeout=common_config[
            "workload_conditional_wait_timeout"
        ],
        workload_command_wait_timeout=common_config["workload_command_wait_timeout"],
        generate_debugging_information_enabled=[
            "generate_debugging_information_enabled"
        ],
        causality_pruning_enabled=common_config["causality_pruning_enabled"],
        effective_updates_pruning_enabled=common_config[
            "effective_updates_pruning_enabled"
        ],
        nondeterministic_pruning_enabled=common_config[
            "nondeterministic_pruning_enabled"
        ],
        persist_test_plans_enabled=common_config["persist_test_plans_enabled"],
        field_key_mask=common_config["field_key_mask"],
        field_path_mask=common_config["field_path_mask"],
        state_update_summary_checker_mask=common_config[
            "state_update_summary_checker_mask"
        ],
        update_oracle_file_enabled=common_config["update_oracle_file_enabled"],
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
        go_mod,
        vendored_controller_runtime_path,
        vendored_client_go_path,
        vendored_sieve_client_path,
        dockerfile_path,
        apis_to_instrument,
        controller_image_name,
        test_command,
        loosen_reconciler_boundary,
        custom_resource_definitions,
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
        self.go_mod = go_mod
        self.vendored_controller_runtime_path = vendored_controller_runtime_path
        self.vendored_client_go_path = vendored_client_go_path
        self.vendored_sieve_client_path = vendored_sieve_client_path
        self.dockerfile_path = dockerfile_path
        self.apis_to_instrument = apis_to_instrument
        self.controller_image_name = controller_image_name
        self.test_command = test_command
        self.loosen_reconciler_boundary = loosen_reconciler_boundary
        self.custom_resource_definitions = custom_resource_definitions
        self.controller_pod_label = controller_pod_label
        self.container_name = container_name
        self.controller_deployment_file_path = controller_deployment_file_path
        self.test_setting = test_setting
        self.end_state_checker_mask = end_state_checker_mask
        self.state_update_summary_checker_mask = state_update_summary_checker_mask


def load_controller_config(controller_config_dir):
    controller_config_path = os.path.join(controller_config_dir, "config.json")
    controller_config = json.load(open(controller_config_path))
    return ControllerConfig(
        controller_name=controller_config["name"],
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
        go_mod=controller_config["go_mod"] if "go_mod" in controller_config else "mod",
        vendored_controller_runtime_path=controller_config[
            "vendored_controller_runtime_path"
        ]
        if "vendored_controller_runtime_path" in controller_config
        else None,
        vendored_client_go_path=controller_config["vendored_client_go_path"]
        if "vendored_client_go_path" in controller_config
        else None,
        vendored_sieve_client_path=controller_config["vendored_sieve_client_path"]
        if "vendored_sieve_client_path" in controller_config
        else None,
        dockerfile_path=controller_config["dockerfile_path"],
        apis_to_instrument=controller_config["apis_to_instrument"]
        if "apis_to_instrument" in controller_config
        else [],
        controller_image_name=controller_config["controller_image_name"],
        test_command=controller_config["test_command"],
        loosen_reconciler_boundary=controller_config["loosen_reconciler_boundary"]
        if "loosen_reconciler_boundary" in controller_config
        else False,
        custom_resource_definitions=controller_config["custom_resource_definitions"],
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
