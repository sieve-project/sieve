from typing import Tuple
import kubernetes
import os
from sieve_common.common import (
    POD,
    PVC,
    STS,
    SECRET,
    SERVICE,
    NO_ERROR_MESSAGE,
    TERMINATED,
    RUNNING,
    BOUND,
    EXIST,
)
import time
import traceback
from sieve_common.config import get_common_config
import datetime
import subprocess
import json

common_config = get_common_config()


def get_pod(resource_name, namespace):
    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    pods = core_v1.list_namespaced_pod(namespace=namespace, watch=False).items
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


def get_pods(resource_name_prefix, namespace):
    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    pods = core_v1.list_namespaced_pod(namespace=namespace, watch=False).items
    target_pods = []
    for pod in pods:
        if pod.metadata.name.startswith(resource_name_prefix):
            target_pods.append(pod)
    return target_pods


def get_sts(resource_name, namespace):
    kubernetes.config.load_kube_config()
    apps_v1 = kubernetes.client.AppsV1Api()
    statefulsets = apps_v1.list_namespaced_stateful_set(
        namespace=namespace, watch=False
    ).items
    target_sts = None
    for sts in statefulsets:
        if sts.metadata.name == resource_name:
            target_sts = sts
    return target_sts


def get_pvc(resource_name, namespace):
    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    pvcs = core_v1.list_namespaced_persistent_volume_claim(
        namespace=namespace, watch=False
    ).items
    target_pvc = None
    for pvc in pvcs:
        if pvc.metadata.name == resource_name:
            target_pvc = pvc
            break
        elif resource_name.endswith("*"):
            resource_name_prefix = resource_name[:-1]
            if pvc.metadata.name.startswith(resource_name_prefix):
                target_pvc = pvc
                break
    return target_pvc


def get_secret(resource_name, namespace):
    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    secrets = core_v1.list_namespaced_secret(namespace=namespace, watch=False).items
    for secret in secrets:
        if secret.metadata.name == resource_name:
            return secret
    return None


def get_service(resource_name, namespace):
    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()
    services = core_v1.list_namespaced_service(namespace=namespace, watch=False).items
    for service in services:
        if service.metadata.name == resource_name:
            return service
    return None


def get_custom_resource(custom_resource_type, resource_name, namespace):
    try:
        custom_resource = json.loads(
            os.popen(
                "kubectl get %s %s -o json -n %s"
                % (custom_resource_type, resource_name, namespace)
            ).read()
        )
        return custom_resource
    except Exception as e:
        print("get custom resource fail", e)
    return None


class TestCmd:
    def __init__(self, cmd, timeout):
        self.cmd = cmd
        self.timeout = timeout

    def run(self) -> Tuple[int, str]:
        print()
        print(self.cmd)
        proc = subprocess.Popen(self.cmd, shell=True)
        try:
            proc.wait(timeout=self.timeout)
            if proc.returncode != 0:
                return 1, "Command error code: '%s' returns %d " % (
                    self.cmd,
                    proc.returncode,
                )
        except subprocess.TimeoutExpired:
            proc.terminate()
            return 2, "Command timeout: '%s' does not finish within %d seconds" % (
                self.cmd,
                self.timeout,
            )
        return 0, NO_ERROR_MESSAGE


class TestWait:
    def __init__(self, time_out):
        self.timeout = time_out

    def run(self) -> Tuple[int, str]:
        print("wait for %s seconds" % str(self.timeout))
        time.sleep(self.timeout)
        return 0, NO_ERROR_MESSAGE


class TestWaitForStatus:
    def __init__(
        self,
        resource_type,
        resource_name,
        status,
        timeout,
        namespace,
    ):
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.status = status
        self.namespace = namespace
        self.timeout = timeout

    def check_pod(self):
        try:
            pod = get_pod(self.resource_name, self.namespace)
        except Exception as err:
            print("error occurs during check pod", err)
            print(traceback.format_exc())
            return False
        if self.status == TERMINATED:
            if pod is None:
                return True
        elif self.status == RUNNING:
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
            pvc = get_pvc(self.resource_name, self.namespace)
        except Exception as err:
            print("error occurs during check pvc", err)
            print(traceback.format_exc())
            return False
        if self.status == TERMINATED:
            if pvc is None:
                return True
        elif self.status == BOUND:
            if pvc is not None and pvc.status.phase == self.status:
                return True
        else:
            assert False, "status not supported yet"
        return False

    def run(self) -> Tuple[int, str]:
        s = time.time()
        print(
            "wait until %s %s becomes %s..."
            % (self.resource_type, self.resource_name, self.status)
        )
        while True:
            duration = time.time() - s
            if duration > self.timeout:
                error_message = (
                    "Conditional wait timeout: %s does not become %s within %d seconds"
                    % (
                        self.resource_name,
                        self.status,
                        self.timeout,
                    )
                )
                print(error_message)
                return 1, error_message
            if self.resource_type == POD:
                if self.check_pod():
                    break
            elif self.resource_type == PVC:
                if self.check_pvc():
                    break
            else:
                assert False, "type not supported yet"
            time.sleep(5)
        time.sleep(5)  # make it configurable
        print("wait takes %f seconds" % (time.time() - s))
        return 0, NO_ERROR_MESSAGE


class TestWaitForNumber:
    def __init__(
        self,
        resource_type,
        resource_name_prefix,
        number,
        timeout,
        namespace,
    ):
        self.resource_type = resource_type
        self.resource_name_prefix = resource_name_prefix
        self.number = number
        self.namespace = namespace
        self.timeout = timeout

    def check_pod(self):
        try:
            pods = get_pods(self.resource_name_prefix, self.namespace)
        except Exception as err:
            print("error occurs during check pod", err)
            print(traceback.format_exc())
            return False
        running_pods = []
        for pod in pods:
            if pod.status.phase == RUNNING:
                running_pods.append(pod)
        return len(running_pods) == self.number

    def run(self) -> Tuple[int, str]:
        s = time.time()
        print(
            "wait until the number of running %s %s becomes %s..."
            % (self.resource_type, self.resource_name_prefix, self.number)
        )
        while True:
            duration = time.time() - s
            if duration > self.timeout:
                error_message = (
                    "Conditional wait timeout: %s does not become %s within %d seconds"
                    % (
                        self.resource_name_prefix,
                        self.number,
                        self.timeout,
                    )
                )
                print(error_message)
                return 1, error_message
            if self.resource_type == POD:
                if self.check_pod():
                    break
            else:
                assert False, "type not supported yet"
            time.sleep(5)
        time.sleep(5)  # make it configurable
        print("wait takes %f seconds" % (time.time() - s))
        return 0, NO_ERROR_MESSAGE


class TestWaitForStorage:
    def __init__(
        self,
        resource_type,
        resource_name,
        storage_size,
        timeout,
        namespace,
    ):
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.storage_size = storage_size
        self.namespace = namespace
        self.timeout = timeout

    def check_sts(self):
        sts = get_sts(self.resource_name, self.namespace)
        if sts is None:
            return False
        for volume_claim_template in sts.spec.volume_claim_templates:
            if (
                volume_claim_template.spec.resources.requests["storage"]
                == self.storage_size
            ):
                return True
        return False

    def run(self) -> Tuple[int, str]:
        s = time.time()
        print(
            "wait until %s %s has storage size %s..."
            % (self.resource_type, self.resource_name, self.storage_size)
        )
        while True:
            duration = time.time() - s
            if duration > self.timeout:
                error_message = (
                    "Conditional wait timeout: %s does not have storage size %s within %d seconds"
                    % (self.resource_name, self.storage_size, self.timeout)
                )
                print(error_message)
                return 1, error_message
            if self.resource_type == STS:
                if self.check_sts():
                    break
            else:
                assert False, "type not supported yet"
            time.sleep(5)
        time.sleep(5)  # make it configurable
        print("wait takes %f seconds" % (time.time() - s))
        return 0, NO_ERROR_MESSAGE


class TestWaitForExistence:
    def __init__(
        self,
        resource_type,
        resource_name,
        exist: bool,
        timeout,
        namespace,
    ):
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.exist = exist
        self.namespace = namespace
        self.timeout = timeout

    def check_secret(self):
        try:
            secret = get_secret(self.resource_name, self.namespace)
        except Exception as err:
            print("error occurs during check pvc", err)
            print(traceback.format_exc())
            return False

        if self.exist == EXIST:
            if secret is not None:
                return True
        else:
            if secret is None:
                return True
        return False

    def check_service(self):
        try:
            service = get_service(self.resource_name, self.namespace)
        except Exception as err:
            print("error occurs during check pvc", err)
            print(traceback.format_exc())
            return False

        if self.exist == EXIST:
            if service is not None:
                return True
        else:
            if service is None:
                return True
        return False

    def run(self) -> Tuple[int, str]:
        s = time.time()
        print(
            "wait until %s %s %s..."
            % (
                self.resource_type,
                self.resource_name,
                "created" if self.exist else "deleted",
            )
        )
        while True:
            duration = time.time() - s
            if duration > self.timeout:
                error_message = (
                    "Conditional wait timeout: %s does not become %s within %d seconds"
                    % (
                        self.resource_name,
                        "created" if self.exist else "deleted",
                        self.timeout,
                    )
                )
                print(error_message)
                return 1, error_message
            if self.resource_type == SECRET:
                if self.check_secret():
                    break
            elif self.resource_type == SERVICE:
                if self.check_service():
                    break
            else:
                assert False, "type not supported yet"
            time.sleep(5)
        time.sleep(5)  # make it configurable
        print("wait takes %f seconds" % (time.time() - s))
        return 0, NO_ERROR_MESSAGE


class TestWaitForCRConditions:
    def __init__(
        self,
        custom_resource_type,
        resource_name,
        conditions,
        timeout,
        namespace,
    ):
        self.custom_resource_type = custom_resource_type
        self.resource_name = resource_name
        self.conditions = conditions
        self.namespace = namespace
        self.timeout = timeout

    def check_cr_conditions(self, custom_resource):
        for condition in self.conditions:
            key_path = condition[0]
            desired_value = condition[1]
            key_path_tokens = key_path.split("/")
            inner_resource = custom_resource
            for token in key_path_tokens:
                if not token in inner_resource:
                    return False
                inner_resource = inner_resource[token]
            if not inner_resource == desired_value:
                return False
        return True

    def run(self) -> Tuple[int, str]:
        s = time.time()
        print(
            "wait until %s %s %s..."
            % (
                self.custom_resource_type,
                self.resource_name,
                self.conditions,
            )
        )
        while True:
            duration = time.time() - s
            if duration > self.timeout:
                error_message = (
                    "Conditional wait timeout: %s does not achieve %s within %d seconds"
                    % (
                        self.resource_name,
                        self.conditions,
                        self.timeout,
                    )
                )
                print(error_message)
                return 1, error_message
            custom_resource = get_custom_resource(
                self.custom_resource_type, self.resource_name, self.namespace
            )
            if custom_resource is None:
                continue
            if self.check_cr_conditions(custom_resource):
                break
            time.sleep(5)
        time.sleep(5)  # make it configurable
        print("wait takes %f seconds" % (time.time() - s))
        return 0, NO_ERROR_MESSAGE


class BuiltInWorkLoad:
    def __init__(self, final_grace_period):
        self.work_list = []
        self.final_grace_period = final_grace_period

    def cmd(self, cmd):
        test_cmd = TestCmd(cmd, timeout=common_config.workload_command_wait_timeout)
        self.work_list.append(test_cmd)
        return self

    def wait_for_pod_number(
        self,
        pod_name_prefix,
        number,
        timeout=common_config.workload_conditional_wait_timeout,
        namespace=common_config.namespace,
    ):
        test_wait = TestWaitForNumber(POD, pod_name_prefix, number, timeout, namespace)
        self.work_list.append(test_wait)
        return self

    def wait_for_pod_status(
        self,
        pod_name,
        status,
        timeout=common_config.workload_conditional_wait_timeout,
        namespace=common_config.namespace,
    ):
        test_wait = TestWaitForStatus(
            POD,
            pod_name,
            status,
            timeout,
            namespace,
        )
        self.work_list.append(test_wait)
        return self

    def wait_for_pvc_status(
        self,
        pvc_name,
        status,
        timeout=common_config.workload_conditional_wait_timeout,
        namespace=common_config.namespace,
    ):
        test_wait = TestWaitForStatus(
            PVC,
            pvc_name,
            status,
            timeout,
            namespace,
        )
        self.work_list.append(test_wait)
        return self

    def wait_for_secret_existence(
        self,
        secret_name,
        exist: bool,
        timeout=common_config.workload_conditional_wait_timeout,
        namespace=common_config.namespace,
    ):
        test_wait = TestWaitForExistence(
            SECRET,
            secret_name,
            exist,
            timeout,
            namespace,
        )
        self.work_list.append(test_wait)
        return self

    def wait_for_service_existence(
        self,
        service_name,
        exist: bool,
        timeout=common_config.workload_conditional_wait_timeout,
        namespace=common_config.namespace,
    ):
        test_wait = TestWaitForExistence(
            SERVICE,
            service_name,
            exist,
            timeout,
            namespace,
        )
        self.work_list.append(test_wait)
        return self

    def wait_for_sts_storage_size(
        self,
        sts_name,
        storage_size,
        timeout=common_config.workload_conditional_wait_timeout,
        namespace=common_config.namespace,
    ):
        test_wait = TestWaitForStorage(
            STS,
            sts_name,
            storage_size,
            timeout,
            namespace,
        )
        self.work_list.append(test_wait)
        return self

    def wait_for_cr_condition(
        self,
        custom_resource_type,
        resource_name,
        conditions,
        timeout=common_config.workload_conditional_wait_timeout,
        namespace=common_config.namespace,
    ):
        test_wait = TestWaitForCRConditions(
            custom_resource_type,
            resource_name,
            conditions,
            timeout,
            namespace,
        )
        self.work_list.append(test_wait)
        return self

    def wait(self, time):
        test_wait = TestWait(time)
        self.work_list.append(test_wait)
        return self

    def run(self, output_file):
        with open(output_file, "w") as f:
            for work in self.work_list:
                return_code, error_message = work.run()
                print(datetime.datetime.now())
                if return_code != 0:
                    print(error_message)
                    f.write(error_message + "\n")
                    if return_code == 2:
                        return
            print()
            print(
                "wait for final grace period %s seconds"
                % (str(self.final_grace_period))
            )
            time.sleep(self.final_grace_period)
            f.write("FINISH-SIEVE-TEST\n")


def new_built_in_workload(final_grace_period=50):
    workload = BuiltInWorkLoad(final_grace_period)
    return workload
