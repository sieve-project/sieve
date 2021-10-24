import os
import sys
import yaml

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

SIEVE_IDX_SKIP = "SIEVE-SKIP"
SIEVE_VALUE_MASK = "SIEVE-NON-NIL"

EXIST = True
NONEXIST = False

KTYPES = [POD, PVC, DEPLOYMENT, STS]

# TODO: we should remove this and use fields in ignore-paths.json instead
BORING_EVENT_OBJECT_FIELDS = [
    "uid",  # random
    "resourceVersion",  # random
    "generation",  # random
    "annotations",  # verbose
    "managedFields",  # verbose
    "lastTransitionTime",  # timing
    "deletionGracePeriodSeconds",  # timing
    "time",  # timing
    "podIP",  # IP assignment is random
    "ip",  # IP assignment is random
    "hostIP",  # IP assignment is random
    "nodeName",  # node assignment is random
    "imageID",  # image ID is randome
    "containerID",  # container ID is random
    "labels",  # label can contain random strings e.g., controller-revision-hash
]

# If paths started with `**/name`, it means we will ignore any key whose name is `name`
# Otherwise, we will match base on he full path
# `x/*/y` * means matching any array index
BORING_EVENT_OBJECT_PATHS = [
    "**/image",
    "**/imageID",
    "**/generation",
    "**/observedGeneration",
    "data",
    "metadata/annotations",
    "metadata/managedFields",
    "metadata/labels",
    "metadata/resourceVersion",
    "metadata/generateName",
    "metadata/ownerReferences",
    "metadata/deletionGracePeriodSeconds",
    "spec/template/spec/containers/*/env",
    "spec/containers/*/env",
    "spec/nodeName",
    "spec/ports",
    "status/conditions",
    "spec/selector/pod-template-hash",
]
BORING_IGNORE_MARK = "SIEVE-IGNORE"

TIME_REG = "^[0-9]+-[0-9]+-[0-9]+T[0-9]+:[0-9]+:[0-9]+Z$"
IP_REG = "^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"

BORING_EVENT_OBJECT_REGS = [TIME_REG, IP_REG]

BORING_POD_LIST = ["csi-hostpathplugin-0", "snapshot-controller-0"]
BORING_STS_LIST = ["csi-hostpathplugin", "snapshot-controller"]


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
    ALL = "all"
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
        num_apiservers=1,
        num_workers=2,
        use_csi_driver=False,
        oracle_config={},
    ):
        self.workload = workload
        self.num_apiservers = num_apiservers
        self.num_workers = num_workers
        self.use_csi_driver = use_csi_driver
        self.oracle_config = oracle_config
        # if self.use_csi_driver:
        #     # For now, we only support one node cluster pvc resizing
        #     self.num_apiservers = 1
        #     self.num_workers = 0


class TestContext:
    def __init__(
        self,
        project,
        test_name,
        stage,
        mode,
        phase,
        test_workload,
        test_config,
        result_dir,
        data_dir,
        docker_repo,
        docker_tag,
        num_apiservers,
        num_workers,
        use_csi_driver,
        oracle_config,
    ):
        self.project = project
        self.test_name = test_name
        self.stage = stage
        self.mode = mode
        self.phase = phase
        self.test_workload = test_workload
        self.test_config = test_config
        self.result_dir = result_dir
        self.data_dir = data_dir
        self.docker_repo = docker_repo
        self.docker_tag = docker_tag
        self.num_apiservers = num_apiservers
        self.num_workers = num_workers
        self.use_csi_driver = use_csi_driver
        self.oracle_config = oracle_config


def dump_to_yaml(file_content, file_name):
    yaml.dump(
        file_content,
        open(
            file_name,
            "w",
        ),
        sort_keys=False,
    )
