import os
import shutil
from sieve_common.common import *
from sieve_oracle.checker_common import *
from sieve_oracle.safety_checker import *
from sieve_oracle.liveness_checker import *
from sieve_oracle.customized_safety_checker import *


def persist_history(test_context: TestContext):
    cprint("Generating state update summary...", bcolors.OKGREEN)
    history = generate_history(test_context)
    history_digest = generate_history_digest(test_context)
    dump_json_file(test_context.result_dir, history, "history.json")
    dump_json_file(test_context.result_dir, history_digest, "event.json")


def persist_state(test_context: TestContext):
    cprint("Generating end state...", bcolors.OKGREEN)
    state = generate_state(test_context)
    dump_json_file(test_context.result_dir, state, "state.json")


def generate_controller_family(test_context: TestContext):
    cprint("Generating controller family list...", bcolors.OKGREEN)
    controller_related_list = generate_controller_related_list(test_context)
    dump_json_file(
        test_context.result_dir, controller_related_list, "controller_family.json"
    )


def canonicalize_history_and_state(test_context: TestContext):
    if not test_context.common_config.update_oracle_file_enabled:
        return
    assert test_context.mode == sieve_modes.GEN_ORACLE
    cprint("Generating canonicalized state update summary...", bcolors.OKGREEN)
    can_history_digest = canonicalize_history_digest(test_context)
    dump_json_file(test_context.oracle_dir, can_history_digest, "event.json")
    cprint("Generating canonicalized end state...", bcolors.OKGREEN)
    can_state = canonicalize_state(test_context)
    dump_json_file(test_context.oracle_dir, can_state, "state.json")
    cprint(
        "Generating canonicalized state mask (for generating test plans)...",
        bcolors.OKGREEN,
    )
    state_mask = generate_state_mask(can_state)
    dump_json_file(test_context.oracle_dir, state_mask, "mask.json")
    cprint(
        "Copying controller family to the oracle dir...",
        bcolors.OKGREEN,
    )
    shutil.copy(
        os.path.join(test_context.result_dir, "controller_family.json"),
        os.path.join(test_context.oracle_dir, "controller_family.json"),
    )


def controller_panic_checker(test_context: TestContext):
    controller_log = os.path.join(test_context.result_dir, "streamed-controller.log")
    messages = []
    file = open(controller_log)
    for line in file.readlines():
        if "Observed a panic" in line:
            panic_in_file = line[line.find("Observed a panic") :]
            messages.append(
                generate_alarm("Exception from controller:", panic_in_file.strip())
            )
    messages.sort()
    return messages


def workload_error_checker(test_context: TestContext):
    workload_log = os.path.join(test_context.result_dir, "workload.log")
    messages = []
    file = open(workload_log)
    for line in file.readlines():
        if line.startswith("FINISH-SIEVE-TEST"):
            break
        if "pauseController" in test_context.action_types and line.startswith(
            "Conditional wait timeout"
        ):
            continue
        messages.append(generate_alarm("Error:", line.strip()))
    messages.sort()
    return messages


def textbook_checker(test_context: TestContext):
    messages = []
    if test_context.common_config.controller_exception_check_enabled:
        panic_messages = controller_panic_checker(test_context)
        messages.extend(panic_messages)

    if test_context.common_config.workload_error_check_enabled:
        workload_messages = workload_error_checker(test_context)
        messages.extend(workload_messages)
    return messages


def safety_checker(test_context: TestContext):
    messages = []
    if test_context.common_config.state_update_summary_check_enabled:
        if not (
            test_context.test_plan_content["actions"] is not None
            and test_context.test_plan_content["actions"][0]["actionType"]
            == "pauseController"
            and test_context.test_plan_content["actions"][0]["pauseAt"]
            == "beforeControllerRead"
        ):
            compare_history_digests_messages = compare_history_digests(test_context)
            messages.extend(compare_history_digests_messages)
    for checker_suite in customized_safety_checker_suites:
        safety_checker_messages = apply_safety_checker(
            test_context,
            checker_suite.resource_keys,
            checker_suite.checker_name,
            checker_suite.checker_function,
        )
        messages.extend(safety_checker_messages)
    return messages


def liveness_checker(test_context: TestContext):
    messages = []
    if test_context.common_config.end_state_check_enabled:
        # TODO: this is overkill; we should exclude the csi related objects only
        if not (
            test_context.use_csi_driver_for_ref and not test_context.use_csi_driver
        ):
            compare_states_messages = compare_states(test_context)
            messages.extend(compare_states_messages)
    return messages


def check(test_context: TestContext):
    common_errors = []
    end_state_errors = []
    history_errors = []
    injection_completed = True
    workload_completed = True

    injection_completed, workload_completed = test_run_validation(test_context)

    textbook_messages = textbook_checker(test_context)
    common_errors.extend(textbook_messages)

    safety_messages = safety_checker(test_context)
    history_errors.extend(safety_messages)

    liveness_messages = liveness_checker(test_context)
    end_state_errors.extend(liveness_messages)

    return TestResult(
        injection_completed=injection_completed,
        workload_completed=workload_completed,
        common_errors=common_errors,
        end_state_errors=end_state_errors,
        history_errors=history_errors,
        no_exception=True,
        exception_message="",
    )
