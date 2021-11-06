from sieve_common.common import *


def generate_time_travel_debugging_hint(test_config_content):
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


def generate_obs_gap_debugging_hint(test_config_content):
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


def generate_obs_gap_debugging_hint(test_config_content):
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


def generate_atom_vio_debugging_hint(test_config_content):
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
    if mode == sieve_modes.TIME_TRAVEL:
        return generate_time_travel_debugging_hint(test_config_content)
    elif mode == sieve_modes.OBS_GAP:
        return generate_obs_gap_debugging_hint(test_config_content)
    elif mode == sieve_modes.ATOM_VIO:
        return generate_atom_vio_debugging_hint(test_config_content)
    else:
        print("mode wrong", mode, test_config_content)
        return "WRONG MODE"


def generate_alarm(sub_alarm, msg):
    return "[ALARM]" + sub_alarm + " " + msg


def generate_warn(msg):
    return "[WARN] " + msg


def generate_fatal(msg):
    return "[FATAL] " + msg


def is_time_travel_started(server_log):
    with open(server_log) as f:
        return "START-SIEVE-TIME-TRAVEL" in f.read()


def is_obs_gap_started(server_log):
    with open(server_log) as f:
        return "START-SIEVE-OBSERVABILITY-GAPS" in f.read()


def is_atom_vio_started(server_log):
    with open(server_log) as f:
        return "START-SIEVE-ATOMICITY-VIOLATION" in f.read()


def is_time_travel_finished(server_log):
    with open(server_log) as f:
        return "FINISH-SIEVE-TIME-TRAVEL" in f.read()


def is_obs_gap_finished(server_log):
    with open(server_log) as f:
        return "FINISH-SIEVE-OBSERVABILITY-GAPS" in f.read()


def is_atom_vio_finished(server_log):
    with open(server_log) as f:
        return "FINISH-SIEVE-ATOMICITY-VIOLATION" in f.read()


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
    if test_mode == sieve_modes.TIME_TRAVEL:
        if not is_time_travel_started(server_log):
            validation_messages.append(generate_warn("time travel is not started yet"))
            validation_ret_val = -1
        elif not is_time_travel_finished(server_log):
            validation_messages.append(generate_warn("time travel is not finished yet"))
            validation_ret_val = -2
    elif test_mode == sieve_modes.OBS_GAP:
        if not is_obs_gap_started(server_log):
            validation_messages.append(generate_warn("obs gap is not started yet"))
            validation_ret_val = -1
        elif not is_obs_gap_finished(server_log):
            validation_messages.append(generate_warn("obs gap is not finished yet"))
            validation_ret_val = -2
    elif test_mode == sieve_modes.ATOM_VIO:
        if not is_atom_vio_started(server_log):
            validation_messages.append(generate_warn("atom vio is not started yet"))
            validation_ret_val = -1
        elif not is_atom_vio_finished(server_log):
            validation_messages.append(generate_warn("atom vio is not finished yet"))
            validation_ret_val = -2
    if not is_test_workload_finished(workload_log):
        validation_messages.append(generate_warn("test workload is not finished yet"))
        validation_ret_val = -3
    validation_messages.sort()
    return validation_ret_val, validation_messages
