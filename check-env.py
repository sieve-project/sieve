import time
import sys
import os
import subprocess


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


def check_go_env():
    if os.system("go version > /dev/null 2>&1") != 0:
        fail("golang environment not detected, please install it according to https://golang.org/doc/install")
        return
    else:
        ok("golang environment detected")

    goenv = {x.split("=")[0]: x.split("=")[1].strip('"') for x in subprocess.check_output(
        "go env", shell=True, encoding='UTF-8').strip().split("\n")}
    if 'GOVERSION' in goenv:
        version = goenv['GOVERSION'][2:]
    else:
        version = os.popen('go version').read().split()[2][2:]
    version_breakdown = version.split(".")
    major = int(version_breakdown[0])
    minor = int(version_breakdown[1])
    if major > 1 or (major == 1 and minor >= 13):
        ok("go version %s satisfies the requirement" %
           (version))
    else:
        warn("go version %s not satisfies the requirement, the minimum go version should be above 1.13.0" % (
            version))

    if 'GOPATH' in os.environ:
        ok("environment variable $GOPATH detected")
    else:
        fail("environment variable $GOPATH not detected, try to set it according to https://golang.org/doc/gopath_code#GOPATH")

    return


def check_kind_env():
    if os.system("kind version > /dev/null 2>&1") != 0:
        fail("kind not detected, please install it according to https://kind.sigs.k8s.io/docs/user/quick-start/#installation")
        return
    else:
        ok("kind detected")

    # version = subprocess.check_output(
    #     "kind version", shell=True, encoding='UTF-8').strip().split()[1]
    version = os.popen("kind version").read().split()[1].split("-")[0]
    parsed = [int(x) for x in (version[1:].split("."))]
    major = parsed[0]
    minor = parsed[1]
    if major > 0 or (major == 0 and minor >= 10):
        ok("kind version %s satisfies the requirement" % (version))
    else:
        warn("kind version %s not satisfies the requirement, the minimum kind version should be above 0.10.0" % (version))

    if 'KUBECONFIG' in os.environ:
        ok("environment variable $KUBECONFIG detected")
    else:
        fail("environment variable $KUBECONFIG not detected, try to set it according to https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig")
    return


def check_sqlite_env():
    warn("sqlite3 version 3.32 and pysqlite3 are only required for learning stage, please ignore the failures below (if any) if you only want to reproduce the bugs")
    if os.system("sqlite3 -version > /dev/null 2>&1") != 0:
        fail("sqlite3 not detected, please install it with version above 3.32 according to https://help.dreamhost.com/hc/en-us/articles/360028047592-Installing-a-custom-version-of-SQLite3")
        return
    else:
        ok("sqlite3 detected")

    version = subprocess.check_output(
        "sqlite3 -version", shell=True, encoding='UTF-8').strip().split()[0]
    major = int(version.split(".")[0])
    minor = int(version.split(".")[1])
    if major > 3 or (major == 3 and minor >= 32):
        ok("sqlite3 version %s satisfies the requirement" % (version))
    else:
        fail("sqlite3 version %s not satisfies the requirement, the minimum sqlite3 version should be above 3.32, please update according to https://help.dreamhost.com/hc/en-us/articles/360028047592-Installing-a-custom-version-of-SQLite3" % (version))

    try:
        import sqlite3
        ok("python module pysqlite3 detected")
    except Exception as err:
        fail("python module pysqlite3 not detected, try to install it by `pip3 install pysqlite3`")


def check_python_env():
    try:
        import kubernetes
        ok("python module kubernetes detected")
    except Exception as err:
        fail("python module pysqlite3 not detected, try to install it by `pip3 install kubernetes`")

    try:
        import yaml
        ok("python module pyyaml detected")
    except Exception as err:
        fail("python module pysqlite3 not detected, try to install it by `pip3 install pyyaml`")


if __name__ == "__main__":
    check_go_env()
    check_kind_env()
    check_python_env()
    check_sqlite_env()
