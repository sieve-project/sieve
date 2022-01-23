from sieve_common.common import *
import copy
from deepdiff import DeepDiff
from sieve_common.default_config import sieve_config


def learn_twice_trim(base_resources, twice_resources):
    def nested_set(dic, keys, value):
        for key in keys[:-1]:
            dic = dic[key]
        dic[keys[-1]] = value

    stored_learn = copy.deepcopy(base_resources)
    ddiff = DeepDiff(twice_resources, base_resources, ignore_order=False, view="tree")

    if "values_changed" in ddiff:
        for key in ddiff["values_changed"]:
            nested_set(
                stored_learn, key.path(output_format="list"), SIEVE_LEARN_VALUE_MASK
            )

    if "dictionary_item_added" in ddiff:
        for key in ddiff["dictionary_item_added"]:
            nested_set(
                stored_learn, key.path(output_format="list"), SIEVE_LEARN_VALUE_MASK
            )

    return stored_learn


def generate_stale_state_debugging_hint(test_config_content):
    desc = "Sieve makes the controller time travel back to the history to see the status just {} {}: {}".format(
        test_config_content["timing"],
        test_config_content["ce-rtype"]
        + "/"
        + test_config_content["ce-namespace"]
        + "/"
        + test_config_content["ce-name"],
        test_config_content["ce-diff-current"],
    )
    suggestion = "Please check how controller reacts when seeing {}: {}, the controller might issue {} to {} without proper checking".format(
        test_config_content["ce-rtype"]
        + "/"
        + test_config_content["ce-namespace"]
        + "/"
        + test_config_content["ce-name"],
        test_config_content["ce-diff-current"],
        "deletion" if test_config_content["se-etype"] == "ADDED" else "creation",
        test_config_content["se-rtype"]
        + "/"
        + test_config_content["se-namespace"]
        + "/"
        + test_config_content["se-name"],
    )
    return desc + "\n" + suggestion + "\n"


def generate_unobserved_state_debugging_hint(test_config_content):
    desc = "Sieve makes the controller miss the event {}: {}".format(
        test_config_content["ce-rtype"]
        + "/"
        + test_config_content["ce-namespace"]
        + "/"
        + test_config_content["ce-name"],
        test_config_content["ce-diff-current"],
    )
    suggestion = "Please check how controller reacts when seeing {}: {}, the event can trigger a controller side effect, and it might be cancelled by following events".format(
        test_config_content["ce-rtype"]
        + "/"
        + test_config_content["ce-namespace"]
        + "/"
        + test_config_content["ce-name"],
        test_config_content["ce-diff-current"],
    )
    return desc + "\n" + suggestion + "\n"


def generate_unobserved_state_debugging_hint(test_config_content):
    desc = "Sieve makes the controller miss the event {}: {}".format(
        test_config_content["ce-rtype"]
        + "/"
        + test_config_content["ce-namespace"]
        + "/"
        + test_config_content["ce-name"],
        test_config_content["ce-diff-current"],
    )
    suggestion = "Please check how controller reacts when seeing {}: {}, the event can trigger a controller side effect, and it might be cancelled by following events".format(
        test_config_content["ce-rtype"]
        + "/"
        + test_config_content["ce-namespace"]
        + "/"
        + test_config_content["ce-name"],
        test_config_content["ce-diff-current"],
    )
    return desc + "\n" + suggestion + "\n"


def generate_intermediate_state_debugging_hint(test_config_content):
    desc = "Sieve makes the controller crash after issuing {} {}: {}".format(
        test_config_content["se-etype-current"],
        test_config_content["se-rtype"]
        + "/"
        + test_config_content["se-namespace"]
        + "/"
        + test_config_content["se-name"],
        test_config_content["se-diff-current"],
    )
    suggestion = "Please check how controller reacts after issuing {} {}: {}, the controller might fail to recover from the dirty state".format(
        test_config_content["se-etype-current"],
        test_config_content["se-rtype"]
        + "/"
        + test_config_content["se-namespace"]
        + "/"
        + test_config_content["se-name"],
        test_config_content["se-diff-current"],
    )
    return desc + "\n" + suggestion + "\n"


def generate_debugging_hint(test_config_content):
    mode = test_config_content["mode"]
    if mode == sieve_modes.STALE_STATE:
        return generate_stale_state_debugging_hint(test_config_content)
    elif mode == sieve_modes.UNOBSR_STATE:
        return generate_unobserved_state_debugging_hint(test_config_content)
    elif mode == sieve_modes.INTERMEDIATE_STATE:
        return generate_intermediate_state_debugging_hint(test_config_content)
    else:
        print("mode wrong", mode, test_config_content)
        return "WRONG MODE"


def generate_alarm(sub_alarm, msg):
    return sub_alarm + " " + msg


def generate_warn(msg):
    return "[WARN] " + msg


def generate_fatal(msg):
    return "[FATAL] " + msg


def is_stale_state_started(server_log):
    with open(server_log) as f:
        return "START-SIEVE-STALE-STATE" in f.read()


def is_unobserved_state_started(server_log):
    with open(server_log) as f:
        return "START-SIEVE-UNOBSERVED-STATE" in f.read()


def is_intermediate_state_started(server_log):
    with open(server_log) as f:
        return "START-SIEVE-INTERMEDIATE-STATE" in f.read()


def is_stale_state_finished(server_log):
    with open(server_log) as f:
        return "FINISH-SIEVE-STALE-STATE" in f.read()


def is_unobserved_state_finished(server_log):
    with open(server_log) as f:
        return "FINISH-SIEVE-UNOBSERVED-STATE" in f.read()


def is_intermediate_state_finished(server_log):
    with open(server_log) as f:
        return "FINISH-SIEVE-INTERMEDIATE-STATE" in f.read()


def is_test_workload_finished(workload_log):
    with open(workload_log) as f:
        return "FINISH-SIEVE-TEST" in f.read()


def injection_validation(test_context: TestContext):
    test_config = test_context.test_config
    server_log = os.path.join(test_context.result_dir, "sieve-server.log")
    workload_log = os.path.join(test_context.result_dir, "workload.log")
    test_config_content = yaml.safe_load(open(test_config))
    test_mode = test_config_content["mode"]
    validation_ret_val = 0
    validation_messages = []
    if test_mode == sieve_modes.STALE_STATE:
        if not is_stale_state_started(server_log):
            validation_messages.append(generate_warn("stale state is not started yet"))
            validation_ret_val = -1
        elif not is_stale_state_finished(server_log):
            validation_messages.append(generate_warn("stale state is not finished yet"))
            validation_ret_val = -2
    elif test_mode == sieve_modes.UNOBSR_STATE:
        if not is_unobserved_state_started(server_log):
            validation_messages.append(
                generate_warn("unobserved state is not started yet")
            )
            validation_ret_val = -1
        elif not is_unobserved_state_finished(server_log):
            validation_messages.append(
                generate_warn("unobserved state is not finished yet")
            )
            validation_ret_val = -2
    elif test_mode == sieve_modes.INTERMEDIATE_STATE:
        if not is_intermediate_state_started(server_log):
            validation_messages.append(
                generate_warn("intermediate state is not started yet")
            )
            validation_ret_val = -1
        elif not is_intermediate_state_finished(server_log):
            validation_messages.append(
                generate_warn("intermediate state is not finished yet")
            )
            validation_ret_val = -2
    if not is_test_workload_finished(workload_log):
        validation_messages.append(generate_warn("test workload is not finished yet"))
        validation_ret_val = -3
    validation_messages.sort()
    return validation_ret_val, validation_messages


def print_error_and_debugging_info(ret_val, messages, test_config):
    if ret_val == 0:
        return
    test_config_content = yaml.safe_load(open(test_config))
    report_color = bcolors.FAIL if ret_val > 0 else bcolors.WARNING
    cprint("Return value: {}\n".format(ret_val) + messages, report_color)
    if sieve_config["injection_desc_generation_enabled"]:
        hint = "[DEBUGGING SUGGESTION]\n" + generate_debugging_hint(test_config_content)
        cprint(hint, bcolors.WARNING)
