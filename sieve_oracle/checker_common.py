from sieve_common.common import *
import copy
from deepdiff import DeepDiff
from sieve_common.k8s_event import (
    APIEventTypes,
    OperatorWriteTypes,
    SIEVE_API_EVENT_MARK,
    parse_api_event,
    parse_key,
)


def kind_native_objects(key: str):
    rtype, ns, name = parse_key(key)
    if rtype == "endpoints" and name == "kubernetes":
        return True
    elif rtype == "secret" and name.startswith("default-token-") and len(name) == 19:
        return True
    elif rtype == "serviceaccount" and name == "default":
        return True
    elif rtype == "service" and name == "kubernetes":
        return True
    elif rtype == "endpointslice" and name == "kubernetes":
        return True
    return False


def get_reference_controller_related_list(test_context: TestContext):
    return json.load(
        open(os.path.join(test_context.oracle_dir, "controller_family.json"))
    )


def get_current_controller_related_list(test_context: TestContext):
    return json.load(
        open(os.path.join(test_context.result_dir, "controller_family.json"))
    )


def generate_controller_related_list(test_context: TestContext):
    log_dir = test_context.result_dir
    api_log_path = os.path.join(log_dir, "apiserver1.log")
    api_event_list = []
    controller_related_list = []
    controller_related_uid_set = set()
    for line in open(api_log_path).readlines():
        if SIEVE_API_EVENT_MARK not in line:
            continue
        api_event = parse_api_event(line)
        api_event_list.append(api_event)
    for api_event in api_event_list:
        if api_event.rtype == "pod":
            pod_as_map = api_event.obj_map
            if "labels" in pod_as_map and "sievetag" in pod_as_map["labels"]:
                controller_related_uid_set.add(pod_as_map["uid"])
                for owner_reference in pod_as_map["ownerReferences"]:
                    controller_related_uid_set.add(owner_reference["uid"])
    keep_tainting = True
    while keep_tainting:
        keep_tainting = False
        for api_event in api_event_list:
            if api_event.get_metadata_value("ownerReferences") is None:
                continue
            if api_event.get_metadata_value("uid") in controller_related_uid_set:
                for owner_reference in api_event.get_metadata_value("ownerReferences"):
                    if owner_reference["uid"] not in controller_related_uid_set:
                        controller_related_uid_set.add(owner_reference["uid"])
                        keep_tainting = True
            else:
                for owner_reference in api_event.get_metadata_value("ownerReferences"):
                    if owner_reference["uid"] in controller_related_uid_set:
                        controller_related_uid_set.add(
                            api_event.get_metadata_value("uid")
                        )
                        keep_tainting = True
    for api_event in api_event_list:
        if (
            api_event.get_metadata_value("uid") in controller_related_uid_set
            and api_event.key not in controller_related_list
        ):
            controller_related_list.append(api_event.key)
    controller_related_list.sort()
    return controller_related_list


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


def readable_resource_diff(event_type, diff_content):
    if (
        event_type == OperatorWriteTypes.CREATE
        or event_type == OperatorWriteTypes.DELETE
        or event_type == APIEventTypes.ADDED
        or event_type == APIEventTypes.DELETED
    ):
        return ""
    else:
        return " : %s" % diff_content


def generate_alarm(sub_alarm, msg):
    return sub_alarm + " " + msg


def generate_warn(msg):
    return "[WARN] " + msg


def generate_fatal(msg):
    return "[FATAL] " + msg


def is_injection_finished(server_log):
    with open(server_log) as f:
        return "Sieve test coordinator finishes all actions" in f.read()


def is_test_workload_finished(workload_log):
    with open(workload_log) as f:
        return "FINISH-SIEVE-TEST" in f.read()


def test_run_validation(test_context: TestContext):
    server_log = os.path.join(test_context.result_dir, "sieve-server.log")
    workload_log = os.path.join(test_context.result_dir, "workload.log")
    injection_completed = True
    workload_completed = True
    if not is_injection_finished(server_log):
        injection_completed = False
    if not is_test_workload_finished(workload_log):
        workload_completed = False
    return injection_completed, workload_completed


def convert_occurrence(occurrence):
    if occurrence.endswith("1"):
        return occurrence + "st"
    elif occurrence.endswith("2"):
        return occurrence + "nd"
    elif occurrence.endswith("3"):
        return occurrence + "rd"
    else:
        return occurrence + "th"


def generate_perturbation_description(test_context: TestContext):
    test_plan_content = yaml.safe_load(open(test_context.test_config))
    if test_plan_content["actions"] is None:
        return "Sieve does not perform any actions."
    desc = ""
    controller_pod_label = test_context.controller_config.controller_pod_label
    for action in test_plan_content["actions"]:
        action_type = action["actionType"]
        action_desc = "Sieve "
        if action_type == "pauseAPIServer":
            action_desc += "pauses the API server {}".format(action["apiServerName"])
        elif action_type == "resumeAPIServer":
            action_desc += "resumes the API server {}".format(action["apiServerName"])
        elif action_type == "pauseController":
            action_desc += "pauses the controller {} ".format(controller_pod_label)
            pause_at = action["pauseAt"]
            if pause_at == "beforeControllerRead":
                action_desc += "before the controller reads "
            elif pause_at == "afterControllerRead":
                action_desc += "after the controller reads "
            elif pause_at == "beforeControllerWrite":
                action_desc += "before the controller writes "
            elif pause_at == "afterControllerWrite":
                action_desc += "after the controller writes "
            else:
                assert False
            if "pauseScope" not in action:
                action_desc += "any object"
            elif action["pauseScope"] == "all":
                action_desc += "any object"
            else:
                action_desc += action["pauseScope"]
        elif action_type == "resumeController":
            action_desc += "resumes the controller {}".format(controller_pod_label)
        elif action_type == "restartController":
            action_desc += "restarts the controller {}".format(controller_pod_label)
        elif action_type == "reconnectController":
            action_desc += "reconnects the controller {} from API server {} to API server {}".format(
                controller_pod_label,
                test_context.common_config.leading_api,
                action["reconnectAPIServer"],
            )
        else:
            assert False
        action_desc += " when the trigger expression {} is satisfied, where\n".format(
            action["trigger"]["expression"]
        )
        for trigger in action["trigger"]["definitions"]:
            action_desc += "{} is satisfied ".format(trigger["triggerName"])
            cond_type = trigger["condition"]["conditionType"]
            if cond_type == "onTimeout":
                action_desc += "by a {}-second timeout.\n".format(
                    trigger["condition"]["timeoutValue"]
                )
            elif cond_type == "onAnnotatedAPICall":
                module = trigger["condition"]["module"]
                file_path = trigger["condition"]["filePath"]
                receiver_type = trigger["condition"]["receiverType"]
                fun_name = trigger["condition"]["funName"]
                occurrence = trigger["condition"]["occurrence"]
                observed_when = trigger["observationPoint"]["when"]
                if observed_when == "beforeAnnotatedAPICall":
                    action_desc += (
                        "before the annotated API {}.{} (in {} from module {})".format(
                            receiver_type, fun_name, file_path, module
                        )
                    )
                elif observed_when == "afterAnnotatedAPICall":
                    action_desc += (
                        "after the annotated API {}.{} (in {} from module {})".format(
                            receiver_type, fun_name, file_path, module
                        )
                    )
                else:
                    assert False
                action_desc += " is called with the {} occurrence.\n".format(
                    convert_occurrence(str(occurrence))
                )
            else:
                observed_when = trigger["observationPoint"]["when"]
                resource_key = trigger["condition"]["resourceKey"]
                occurrence = trigger["condition"]["occurrence"]
                if observed_when == "beforeAPIServerRecv":
                    action_desc += (
                        "before the API server {} receives the event:\n".format(
                            trigger["observationPoint"]["by"]
                        )
                    )
                elif observed_when == "afterAPIServerRecv":
                    action_desc += (
                        "after the API server {} receives the event:\n".format(
                            trigger["observationPoint"]["by"]
                        )
                    )
                elif observed_when == "beforeControllerRecv":
                    action_desc += (
                        "before the controller {} receives the event:\n".format(
                            controller_pod_label
                        )
                    )
                elif observed_when == "afterControllerRecv":
                    action_desc += (
                        "after the controller {} receives the event:\n".format(
                            controller_pod_label
                        )
                    )
                elif observed_when == "beforeControllerWrite":
                    action_desc += "before the controller {} issues:\n".format(
                        controller_pod_label
                    )
                elif observed_when == "afterControllerWrite":
                    action_desc += "after the controller {} issues:\n".format(
                        controller_pod_label
                    )
                if cond_type == "onObjectCreate":
                    action_desc += "create {} ".format(resource_key)
                elif cond_type == "onObjectDelete":
                    action_desc += "delete {} ".format(resource_key)
                elif cond_type == "onObjectUpdate":
                    action_desc += "update {} ".format(resource_key)
                    if "prevStateDiff" in trigger["condition"]:
                        action_desc += "from\n{}\nto\n{}\n".format(
                            trigger["condition"]["prevStateDiff"],
                            trigger["condition"]["curStateDiff"],
                        )
                elif cond_type == "onAnyFieldModification":
                    action_desc += (
                        "update {} so that any field in\n{}\nis modified ".format(
                            resource_key, trigger["condition"]["prevStateDiff"]
                        )
                    )
                action_desc += "with the {} occurrence.\n".format(
                    convert_occurrence(str(occurrence))
                )
        desc += action_desc
    return desc


def print_error_and_debugging_info(test_context: TestContext, test_result: TestResult):
    if not test_result.injection_completed:
        cprint("injection is not completed", bcolors.WARNING)

    if not test_result.workload_completed:
        cprint("workload is not completed", bcolors.WARNING)

    if len(test_result.common_errors) > 0:
        cprint(
            "{} detected common errors as follows".format(
                len(test_result.common_errors)
            ),
            bcolors.FAIL,
        )
        cprint("\n".join(test_result.common_errors) + "\n", bcolors.FAIL)

    if len(test_result.end_state_errors) > 0:
        cprint(
            "{} detected end state inconsistencies as follows".format(
                len(test_result.end_state_errors)
            ),
            bcolors.FAIL,
        )
        cprint("\n".join(test_result.end_state_errors) + "\n", bcolors.FAIL)

    if len(test_result.history_errors) > 0:
        cprint(
            "{} detected history inconsistencies as follows".format(
                len(test_result.history_errors)
            ),
            bcolors.FAIL,
        )
        cprint("\n".join(test_result.history_errors) + "\n", bcolors.FAIL)

    if test_context.common_config.generate_debugging_information_enabled:
        desc = "[PERTURBATION DESCRIPTION]\n" + generate_perturbation_description(
            test_context
        )
        print(desc)
