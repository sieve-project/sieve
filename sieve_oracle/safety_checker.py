from sieve_common.common import *
import json
from sieve_oracle.checker_common import *


def get_learning_history_digest(test_context: TestContext):
    learning_history_digest = json.load(
        open(os.path.join(test_context.oracle_dir, "event.json"))
    )
    return learning_history_digest


def get_testing_history_digest(test_context: TestContext):
    testing_history_digest = json.load(
        open(os.path.join(test_context.result_dir, "event.json"))
    )
    return testing_history_digest


def get_testing_history(test_context: TestContext):
    testing_history = json.load(
        open(os.path.join(test_context.result_dir, "history.json"))
    )
    return testing_history


def check_single_history(history, resource_keys, checker_name, customized_checker):
    ret_val = 0
    messages = []
    current_state = {}
    for key in resource_keys:
        current_state[key] = None
    for event in history:
        if event["key"] in resource_keys:
            if event["etype"] == "DELETED":
                current_state[event["key"]] = None
            else:
                current_state[event["key"]] = event["state"]
            existing_resource_cnt = 0
            for key in current_state:
                if current_state[key] is not None:
                    existing_resource_cnt += 1
            if existing_resource_cnt == len(current_state):
                if not customized_checker(current_state):
                    ret_val += 1
                    messages.append(
                        generate_alarm(
                            "[CUSTOMIZED-SAFETY]",
                            "checker {} failed on {}".format(
                                checker_name, current_state
                            ),
                        )
                    )
    return ret_val, messages
