import os
import sys

NO_ERROR_MESSAGE = ""

POD = "pod"
PVC = "persistentvolumeclaim"
DEPLOYMENT = "deployment"
STS = "statefulset"
SECRET = "secret"
SERVICE = "service"

PENDING = "Pending"
RUNNING = "Running"
TERMINATED = "Terminated"
BOUND = "Bound"

SIEVE_SKIP_MARKER = "SIEVE-SKIP"
SIEVE_CANONICALIZATION_MARKER = "SIEVE-NON-NIL"

EXIST = True
NONEXIST = False

KTYPES = [POD, PVC, DEPLOYMENT, STS]

BORING_EVENT_OBJECT_FIELDS = [
    "resourceVersion",
    "time",
    "managedFields",
    "lastTransitionTime",
    "generation",
    "annotations",
    "deletionGracePeriodSeconds",
]

TIME_REG = "^[0-9]+-[0-9]+-[0-9]+T[0-9]+:[0-9]+:[0-9]+Z$"
IP_REG = "^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"


def cmd_early_exit(cmd, early_exit=True):
    return_code = os.WEXITSTATUS(os.system(cmd))
    if return_code != 0 and early_exit:
        fail(cmd)
        sys.exit(1)
    return return_code


class sieve_stages:
    LEARN = "learn"
    TEST = "test"


class sieve_modes:
    TIME_TRAVEL = "time-travel"
    OBS_GAP = "observability-gap"
    ATOM_VIO = "atomicity-violation"
    VANILLA = "vanilla"
    LEARN_ONCE = "learn-once"
    LEARN_TWICE = "learn-twice"
    NONE = "none"


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def warn(message):
    print(bcolors.WARNING + "[WARN] " + message + bcolors.ENDC)


def ok(message):
    print(bcolors.OKGREEN + "[OK] " + message + bcolors.ENDC)


def fail(message):
    print(bcolors.FAIL + "[FAIL] " + message + bcolors.ENDC)


def cprint(message, color):
    print(color + message + bcolors.ENDC)


class Suite:
    def __init__(
        self,
        workload,
        two_sided=False,
        num_apiservers=1,
        num_workers=2,
        pvc_resize=False,
        oracle_config={},
    ):
        self.workload = workload
        self.two_sided = two_sided
        self.num_apiservers = num_apiservers
        self.num_workers = num_workers
        self.pvc_resize = pvc_resize
        self.oracle_config = oracle_config
        if self.pvc_resize:
            # For now, we only support one node cluster pvc resizing
            self.num_apiservers = 1
            self.num_workers = 0
