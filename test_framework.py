import kubernetes
import os
import common
import time


class TestCmd:
    def __init__(self, cmd):
        self.cmd = cmd

    def run(self):
        print(self.cmd)
        # TODO: need to check the return code of the os.system
        os.system(self.cmd)
        return 0


class TestWait:
    def __init__(self, time_out):
        self.time_out = time_out

    def run(self):
        print("wait for %s seconds" % str(self.time_out))
        time.sleep(self.time_out)
        return 0


class TestWaitForStatus:
    def __init__(self, resource_type, resource_name, status, time_out="600"):
        assert resource_type == common.POD  # TODO: support other types
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.status = status
        self.namespace = "default"
        self.time_out = time_out

    def run(self):
        s = time.time()
        if self.resource_type == common.POD:
            print("wait until pod %s becomes %s..." %
                  (self.resource_name, self.status))
            kubernetes.config.load_kube_config()
            core_v1 = kubernetes.client.CoreV1Api()
            while True:
                if time.time() - s > float(self.time_out):
                    print("[ERROR] waiting timeout: %s does not become %s within %d seconds" %
                          (self.resource_name, self.status, self.time_out))
                    return 1
                pods = core_v1.list_namespaced_pod(
                    namespace="default", watch=False).items
                not_found = True
                status = ""
                for pod in pods:
                    if pod.metadata.name == self.resource_name:
                        not_found = False
                        status = pod.status.phase
                if self.status == common.TERMINATED:
                    if not_found:
                        break
                else:
                    if status == self.status:
                        break
                time.sleep(5)
        else:
            assert False, "types other than pod not supported yet"
        print("wait takes %f seconds" % (time.time() - s))
        return 0


class BuiltInWorkLoad:
    def __init__(self):
        self.work_list = []

    def cmd(self, cmd):
        test_cmd = TestCmd(cmd)
        self.work_list.append(test_cmd)
        return self

    def wait_for_pod_status(self, pod_name, status):
        test_wait = TestWaitForStatus(common.POD, pod_name, status)
        self.work_list.append(test_wait)
        return self

    def wait(self, time):
        test_wait = TestWait(time)
        self.work_list.append(test_wait)
        return self

    def run(self, mode="ignore"):
        for work in self.work_list:
            if work.run() != 0:
                print("[ERROR] cannot fullfill workload")
                return 1


def new_built_in_workload():
    workload = BuiltInWorkLoad()
    return workload


class ExtendedWorkload:
    def __init__(self, test_dir, test_cmd, check_mode=False):
        self.test_dir = test_dir
        self.test_cmd = test_cmd
        self.check_mode = check_mode

    def run(self, mode):
        org_dir = os.getcwd()
        os.chdir(self.test_dir)
        # TODO: need to check the return code of the os.system
        if self.check_mode:
            os.system(self.test_cmd + " " + mode)
        else:
            os.system(self.test_cmd)
        os.chdir(org_dir)
        return 0
