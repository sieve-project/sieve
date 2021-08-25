import kubernetes
import os
import common
import time
import traceback
import sieve_config


def get_pod(resource_name):
    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    pods = core_v1.list_namespaced_pod(
        namespace=sieve_config.config["namespace"], watch=False).items
    target_pod = None
    for pod in pods:
        if pod.metadata.name == resource_name:
            target_pod = pod
            break
        elif resource_name.endswith("*"):
            resource_name_prefix = resource_name[:-1]
            if pod.metadata.name.startswith(resource_name_prefix):
                target_pod = pod
                break
    return target_pod


def get_sts(resource_name):
    kubernetes.config.load_kube_config()
    apps_v1 = kubernetes.client.AppsV1Api()
    statefulsets = apps_v1.list_namespaced_stateful_set(
        namespace=sieve_config.config["namespace"], watch=False).items
    target_sts = None
    for sts in statefulsets:
        if sts.metadata.name == resource_name:
            target_sts = sts
    return target_sts


def get_pvc(resource_name):
    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    pvcs = core_v1.list_namespaced_persistent_volume_claim(
        namespace=sieve_config.config["namespace"], watch=False).items
    target_pvc = None
    for pvc in pvcs:
        if pvc.metadata.name == resource_name:
            target_pvc = pvc
    return target_pvc


class TestCmd:
    def __init__(self, cmd):
        self.cmd = cmd

    def run(self, mode):
        print(self.cmd)
        # TODO: need to check the return code of the os.system
        os.system(self.cmd)
        return 0


class TestWait:
    def __init__(self, time_out):
        self.time_out = time_out

    def run(self, mode):
        print("wait for %s seconds" % str(self.time_out))
        time.sleep(self.time_out)
        return 0


class TestWaitForStatus:
    def __init__(self, resource_type, resource_name, status, obs_gap_waiting_time, time_out=600):
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.status = status
        self.namespace = sieve_config.config["namespace"]
        self.obs_gap_waiting_time = obs_gap_waiting_time
        self.time_out = time_out

    def check_pod(self):
        try:
            pod = get_pod(self.resource_name)
        except Exception as err:
            print("error occurs during check pod", err)
            print(traceback.format_exc())
            return False
        if self.status == common.TERMINATED:
            if pod is None:
                return True
        elif self.status == common.RUNNING:
            if pod is not None and pod.status.phase == self.status:
                all_ready = True
                for container_status in pod.status.container_statuses:
                    if not container_status.ready:
                        all_ready = False
                if all_ready:
                    return True
        else:
            assert False, "status not supported yet"
        return False

    def check_pvc(self):
        try:
            pvc = get_pvc(self.resource_name)
        except Exception as err:
            print("error occurs during check pvc", err)
            print(traceback.format_exc())
            return False
        if self.status == common.TERMINATED:
            if pvc is None:
                return True
        elif self.status == common.BOUND:
            if pvc is not None and pvc.status.phase == self.status:
                return True
        else:
            assert False, "status not supported yet"
        return False

    def run(self, mode):
        s = time.time()
        print("wait until %s %s becomes %s..." %
              (self.resource_type, self.resource_name, self.status))
        if mode == "obs-gap" and self.obs_gap_waiting_time != -1:
            time.sleep(self.obs_gap_waiting_time)
            print("obs gap waiting time is reached")
        else:
            while True:
                if time.time() - s > float(self.time_out):
                    print("[ERROR] waiting timeout: %s does not become %s within %d seconds" %
                          (self.resource_name, self.status, self.time_out))
                    os.system("kubectl describe pods")
                    return 1
                if self.resource_type == common.POD:
                    if self.check_pod():
                        break
                elif self.resource_type == common.PVC:
                    if self.check_pvc():
                        break
                else:
                    assert False, "type not supported yet"
                time.sleep(5)
        print("wait takes %f seconds" % (time.time() - s))
        return 0


class TestWaitForStorage:
    def __init__(self, resource_type, resource_name, storage_size, obs_gap_waiting_time, time_out=600):
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.storage_size = storage_size
        self.namespace = sieve_config.config["namespace"]
        self.obs_gap_waiting_time = obs_gap_waiting_time
        self.time_out = time_out

    def check_sts(self):
        sts = get_sts(self.resource_name)
        if sts is None:
            return False
        for volume_claim_template in sts.spec.volume_claim_templates:
            if volume_claim_template.spec.resources.requests["storage"] == self.storage_size:
                return True
        return True

    def run(self, mode):
        s = time.time()
        print("wait until %s %s has storage size %s..." %
              (self.resource_type, self.resource_name, self.storage_size))
        if mode == "obs-gap" and self.obs_gap_waiting_time != -1:
            time.sleep(self.obs_gap_waiting_time)
            print("obs gap waiting time is reached")
        else:
            while True:
                if time.time() - s > float(self.time_out):
                    print("[ERROR] waiting timeout: %s does not have storage size %s within %d seconds" %
                          (self.resource_name, self.storage_size, self.time_out))
                    return 1
                if self.resource_type == common.STS:
                    if self.check_sts():
                        break
                else:
                    assert False, "type not supported yet"
                time.sleep(5)
        print("wait takes %f seconds" % (time.time() - s))
        return 0


class BuiltInWorkLoad:
    def __init__(self):
        self.work_list = []

    def cmd(self, cmd):
        test_cmd = TestCmd(cmd)
        self.work_list.append(test_cmd)
        return self

    def wait_for_pod_status(self, pod_name, status, obs_gap_waiting_time=-1):
        test_wait = TestWaitForStatus(
            common.POD, pod_name, status, obs_gap_waiting_time)
        self.work_list.append(test_wait)
        return self

    def wait_for_pvc_status(self, pvc_name, status, obs_gap_waiting_time=-1):
        test_wait = TestWaitForStatus(
            common.PVC, pvc_name, status, obs_gap_waiting_time)
        self.work_list.append(test_wait)
        return self

    def wait_for_sts_storage_size(self, sts_name, storage_size, obs_gap_waiting_time=-1):
        test_wait = TestWaitForStorage(
            common.STS, sts_name, storage_size, obs_gap_waiting_time)
        self.work_list.append(test_wait)
        return self

    def wait(self, time):
        test_wait = TestWait(time)
        self.work_list.append(test_wait)
        return self

    def run(self, mode):
        for work in self.work_list:
            # print(work, str(datetime.now()))
            if work.run(mode) != 0:
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
