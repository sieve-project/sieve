import json


class SafetyCheckerSuite:
    def __init__(self, resource_keys, checker_name, checker_function):
        self.resource_keys = resource_keys
        self.checker_name = checker_name
        self.checker_function = checker_function


# Customized safety checker example:
# This checker checks a safety property:
# The rattbitmq-cluster-server statefulset should never have more than one replica
# (the property is not correct; this is just an example)
# Sieve will apply this checker to every state
# As long as there is one state where the property does not hold (return false in the function)
# Sieve will report an alarm
def example_safety_checker(state):
    key = "statefulset/default/rabbitmq-cluster-server"
    if key in state:
        object_state = json.loads(state[key])
        # print(object_state)
        if object_state["Spec"]["Replicas"] > 1:
            return False
    return True


# Users can specify customized safety checker by adding SafetyCheckerSuite here
# Each SafetyCheckerSuite has three elements:
# 1. the list of resources to check, here there is only one resource to check: statefulset/default/rabbitmq-cluster-server
# 2. the checker's name
# 3. the checker function
customized_safety_checker_suites = [
    # SafetyCheckerSuite(
    #     ["statefulset/default/rabbitmq-cluster-server"],
    #     "example_checker",
    #     example_safety_checker,
    # )
]
