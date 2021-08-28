POD = "pod"
PVC = "persistentvolumeclaim"
DEPLOYMENT = "deployment"
STS = "statefulset"

PENDING = "Pending"
RUNNING = "Running"
TERMINATED = "Terminated"
BOUND = "Bound"

KTYPES = [POD, PVC, DEPLOYMENT, STS]


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def warn(message):
    print(bcolors.WARNING + "[WARN] " + message + bcolors.ENDC)


def ok(message):
    print(bcolors.OKGREEN + "[OK] " + message + bcolors.ENDC)


def fail(message):
    print(bcolors.FAIL + "[FAIL] " + message + bcolors.ENDC)


def cprint(message, color):
    print(color + message + bcolors.ENDC)
