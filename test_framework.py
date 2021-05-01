import kubernetes
import os
import common
import time


class TestCmd:
    def __init__(self, cmd):
        self.cmd = cmd

    def run(self):
        os.system(self.cmd)


class TestWaitForStatus:
    def __init__(self, resource_type, resource_name, status, time_out="600"):
        assert resource_type == common.POD  # TODO: support other types
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.status = status
        self.namespace = "default"
        self.time_out = time_out

    def run(self):
        if self.resource_type == common.POD:
            kubernetes.config.load_kube_config()
            core_v1 = kubernetes.client.CoreV1Api()
            while True:
                pod = core_v1.read_namespaced_pod(
                    name=self.resource_name, namespace="default")
                if pod is not None and pod.status.phase == self.status:
                    break
                time.sleep(5)
        else:
            assert False, "types other than pod not supported yet"


class TestWorkLoad:
    def __init__(self):
        self.work_list = []

    def cmd(self, cmd):
        test_cmd = TestCmd(cmd)
        self.work_list.append(test_cmd)

    def wait_for_pod_status(self, pod_name, status):
        test_wait = TestWaitForStatus(common.POD, pod_name, status)
        self.work_list.append(test_wait)

    def run(self):
        for work in self.work_list:
            work.run()
