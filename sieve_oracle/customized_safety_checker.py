import json


class SafetyCheckerSuite:
    def __init__(self, resource_keys, checker_name, checker_function):
        self.resource_keys = resource_keys
        self.checker_name = checker_name
        self.checker_function = checker_function


def example_safety_checker(state):
    key = "statefulset/default/rabbitmq-cluster-server"
    if key in state:
        object_state = json.loads(state[key])
        # print(object_state)
        if object_state["Spec"]["Replicas"] > 0:
            return False
    return True


customized_safety_checker_suites = [
    # SafetyCheckerSuite(
    #     ["statefulset/default/rabbitmq-cluster-server"],
    #     "example_checker",
    #     example_safety_checker,
    # )
]
