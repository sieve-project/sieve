import kubernetes
import yaml
import json
import os
from sieve_common.common import *
from sieve_common.default_config import sieve_config
import deepdiff
from deepdiff import DeepDiff
from sieve_oracle.checker_common import *
from sieve_oracle.safety_checker import *


def persistent_history_and_state(
    test_context: TestContext, canonicalize_resource=False
):
    if sieve_config["generic_event_generation_enabled"]:
        history = generate_history(test_context)
        history_digest = generate_history_digest(test_context)
        dump_json_file(test_context.result_dir, history, "history.json")
        dump_json_file(test_context.result_dir, history_digest, "event.json")
    if sieve_config["generic_state_generation_enabled"]:
        resources = generate_state(test_context.result_dir, canonicalize_resource)
        ignore_paths = generate_ignore_paths(resources)
        # we generate state.json at src_dir (log dir)
        dump_json_file(test_context.result_dir, resources, "state.json")
        dump_json_file(test_context.result_dir, ignore_paths, "mask.json")
        # we generate state.json at dest_dir (data dir) if cononicalize_resource=True
        if canonicalize_resource:
            dump_json_file(test_context.oracle_dir, resources, "state.json")
            dump_json_file(test_context.oracle_dir, ignore_paths, "mask.json")


def canonicalize_history_and_state(test_context: TestContext):
    assert test_context.mode == sieve_modes.LEARN_TWICE
    can_history_digest = canonicalize_history_digest(test_context)
    dump_json_file(test_context.oracle_dir, can_history_digest, "event.json")


def operator_checker(test_context: TestContext):
    operator_log = os.path.join(test_context.result_dir, "streamed-operator.log")
    ret_val = 0
    messages = []
    file = open(operator_log)
    for line in file.readlines():
        if "Observed a panic" in line:
            panic_in_file = line[line.find("Observed a panic") :]
            messages.append(generate_alarm("[OPERATOR-PANIC]", panic_in_file.strip()))
            ret_val += 1
    messages.sort()
    return ret_val, messages


def test_workload_checker(test_context: TestContext):
    workload_log = os.path.join(test_context.result_dir, "workload.log")
    ret_val = 0
    messages = []
    file = open(workload_log)
    for line in file.readlines():
        if line.startswith("error:"):
            ret_val += 1
            messages.append(generate_alarm("[WORKLOAD]", line.strip()))
    messages.sort()
    return ret_val, messages


def equal_path(template, value):
    template = template.split("/")
    value = value.split("/")

    if len(template) > len(value):
        return False

    for i in range(len(template)):
        if template[i] == "*":
            continue
        if template[i] != value[i]:
            return False
    return True


def preprocess(learn, test):
    for resource in list(learn):
        if resource not in test:
            learn.pop(resource, None)
    for resource in list(test):
        if resource not in learn:
            test.pop(resource, None)


def generic_state_checker(test_context: TestContext):
    learn = json.load(open(os.path.join(test_context.oracle_dir, "state.json")))
    test = json.load(open(os.path.join(test_context.result_dir, "state.json")))

    ret_val = 0
    messages = []

    def nested_get(dic, keys):
        for key in keys:
            dic = dic[key]
        return dic

    preprocess(learn, test)
    tdiff = DeepDiff(learn, test, ignore_order=False, view="tree")
    resource_map = {resource: {"add": [], "remove": []} for resource in test}
    boring_keys = set(gen_mask_keys())
    boring_paths = set(gen_mask_paths())

    for delta_type in tdiff:
        for key in tdiff[delta_type]:
            path = key.path(output_format="list")

            # Handle for resource size diff
            if len(path) == 2:
                resource_type = path[0]
                name = path[1]
                if key.t1 == SIEVE_LEARN_VALUE_MASK:
                    name = SIEVE_LEARN_VALUE_MASK
                resource_map[resource_type][
                    "add" if delta_type == "dictionary_item_added" else "remove"
                ].append(name)
                continue

            if delta_type in ["values_changed", "type_changes"]:
                if (
                    key.t1 == SIEVE_LEARN_VALUE_MASK
                    or match_mask_regex(key.t1)
                    or match_mask_regex(key.t2)
                ):
                    continue

            has_not_care = False
            # Search for boring keys
            for kp in path:
                if kp in boring_keys:
                    has_not_care = True
                    break
            # Search for boring paths
            if len(path) > 2:
                for rule in boring_paths:
                    if equal_path(rule, "/".join([str(x) for x in path[2:]])):
                        has_not_care = True
                        break
            if has_not_care:
                continue

            resource_type = path[0]
            if len(path) == 2 and type(key.t2) is deepdiff.helper.NotPresent:
                source = learn
            else:
                source = test

            name = nested_get(source, path[:2] + ["metadata", "name"])
            namespace = nested_get(source, path[:2] + ["metadata", "namespace"])

            if name == "sieve-testing-global-config":
                continue
            ret_val += 1
            if delta_type in ["dictionary_item_added", "iterable_item_added"]:
                messages.append(
                    generate_alarm(
                        "[RESOURCE-KEY-ADD]",
                        "{} {} {} {} {}".format(
                            "/".join([resource_type, namespace, name]),
                            "/".join(map(str, path[2:])),
                            "not seen during learning run, but seen as",
                            key.t2,
                            "during testing run",
                        ),
                    )
                )
            elif delta_type in ["dictionary_item_removed", "iterable_item_removed"]:
                messages.append(
                    generate_alarm(
                        "[RESOURCE-KEY-REMOVE]",
                        "{} {} {} {} {}".format(
                            "/".join([resource_type, namespace, name]),
                            "/".join(map(str, path[2:])),
                            "seen as",
                            key.t1,
                            "during learning run, but not seen during testing run",
                        ),
                    )
                )
            elif delta_type == "values_changed":
                messages.append(
                    generate_alarm(
                        "[RESOURCE-KEY-DIFF]",
                        "{} {} {} {} {} {} {}".format(
                            "/".join([resource_type, namespace, name]),
                            "/".join(map(str, path[2:])),
                            "is",
                            key.t1,
                            "during learning run, but",
                            key.t2,
                            "during testing run",
                        ),
                    )
                )
            else:
                messages.append(
                    generate_alarm(
                        "[RESOURCE-KEY-UNKNOWN-CHANGE]",
                        "{} {} {} {} {} {} {}".format(
                            delta_type,
                            "/".join([resource_type, namespace, name]),
                            "/".join(map(str, path[2:])),
                            "is",
                            key.t1,
                            " => ",
                            key.t2,
                        ),
                    )
                )

    for resource_type in resource_map:
        resource = resource_map[resource_type]
        if SIEVE_LEARN_VALUE_MASK in resource["add"] + resource["remove"]:
            # Then we only report number diff
            delta = len(resource["add"]) - len(resource["remove"])
            learn_set = set(learn[resource_type].keys())
            test_set = set(test[resource_type].keys())
            if delta != 0:
                ret_val += 1
                messages.append(
                    generate_alarm(
                        "[ALARM][RESOURCE-ADD]"
                        if delta > 0
                        else "[ALARM][RESOURCE-REMOVE]",
                        "{} {} {} {} {} {} {} {} {}".format(
                            len(learn_set),
                            resource_type,
                            "seen after learning run",
                            sorted(learn_set),
                            "but",
                            len(test_set),
                            resource_type,
                            "seen after testing run",
                            sorted(test_set),
                        ),
                    )
                )
        else:
            # We report resource diff detail
            for name in resource["add"]:
                ret_val += 1
                messages.append(
                    generate_alarm(
                        "[ALARM][RESOURCE-ADD]",
                        "{} {}".format(
                            "/".join([resource_type, name]),
                            "is not seen during learning run, but seen during testing run",
                        ),
                    )
                )
            for name in resource["remove"]:
                ret_val += 1
                messages.append(
                    generate_alarm(
                        "[ALARM][RESOURCE-REMOVE]",
                        "{} {}".format(
                            "/".join([resource_type, name]),
                            "is seen during learning run, but not seen during testing run",
                        ),
                    )
                )

    messages.sort()
    return ret_val, messages


def print_error_and_debugging_info(ret_val, messages, test_config):
    if ret_val == 0:
        return
    test_config_content = yaml.safe_load(open(test_config))
    report_color = bcolors.FAIL if ret_val > 0 else bcolors.WARNING
    cprint("[RET VAL] {}\n".format(ret_val) + messages, report_color)
    if sieve_config["injection_desc_generation_enabled"]:
        hint = "[DEBUGGING SUGGESTION]\n" + generate_debugging_hint(test_config_content)
        cprint(hint, bcolors.WARNING)


def safety_checker(test_context: TestContext):
    ret_val = 0
    messages = []
    if (
        sieve_config["generic_event_checker_enabled"]
        and test_context.mode != sieve_modes.OBS_GAP
    ):
        write_ret_val, write_messages = compare_history_digests(test_context)
        ret_val += write_ret_val
        messages.extend(write_messages)
    return ret_val, messages


def check(test_context: TestContext):
    ret_val = 0
    messages = []

    validation_ret_val, validation_messages = injection_validation(test_context)
    if validation_ret_val < 0:
        messages.extend(validation_messages)

    if sieve_config["operator_checker_enabled"]:
        panic_ret_val, panic_messages = operator_checker(test_context)
        ret_val += panic_ret_val
        messages.extend(panic_messages)

    if sieve_config["test_workload_checker_enabled"]:
        workload_ret_val, workload_messages = test_workload_checker(test_context)
        ret_val += workload_ret_val
        messages.extend(workload_messages)

    # if sieve_config["generic_event_checker_enabled"]:
    write_ret_val, write_messages = safety_checker(test_context)
    ret_val += write_ret_val
    messages.extend(write_messages)

    if sieve_config["generic_state_checker_enabled"]:
        resource_ret_val, resource_messages = generic_state_checker(test_context)
        ret_val += resource_ret_val
        messages.extend(resource_messages)

    if validation_ret_val < 0:
        ret_val = validation_ret_val

    return ret_val, "\n".join(messages)
