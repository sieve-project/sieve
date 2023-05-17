import shutil
from typing import Tuple
import docker
import optparse
import os
import kubernetes
from sieve_common.config import (
    get_common_config,
    load_controller_config,
)
import time
import json
import glob
import sys
from sieve_analyzer import analyze
from sieve_oracle.oracle import (
    save_state,
    save_history,
    save_controller_related_object_list,
    create_differential_oracles,
    check,
)
from sieve_oracle.checker_common import (
    print_error_and_debugging_info,
)
import yaml
import subprocess
import signal
import errno
import socket
import traceback
from sieve_common.common import (
    TestContext,
    TestResult,
    cprint,
    bcolors,
    ok,
    fail,
    sieve_modes,
    os_system,
    deploy_directory,
    rmtree_if_exists,
    first_pass_learn_result_dir,
)


def save_run_result(
    test_context: TestContext,
    test_result: TestResult,
    start_time,
):
    """
    Save the testing result into a json file for later debugging.
    The test result json contains the test plan, the errors detected by the oracles and so on.
    """
    if test_context.mode != sieve_modes.TEST:
        return

    if test_result is None:
        assert False, "test result should not be None"

    result_map = {
        test_context.controller: {
            test_context.test_workload: {
                test_context.mode: {
                    test_context.original_test_plan: {
                        "duration": time.time() - start_time,
                        "injection_completed": test_result.injection_completed,
                        "workload_completed": test_result.workload_completed,
                        "number_errors": len(test_result.common_errors)
                        + len(test_result.end_state_errors)
                        + len(test_result.history_errors),
                        "detected_errors": test_result.common_errors
                        + test_result.end_state_errors
                        + test_result.history_errors,
                        "no_exception": test_result.no_exception,
                        "exception_message": test_result.exception_message,
                        "test_plan_content": open(
                            test_context.original_test_plan
                        ).read()
                        if test_context.mode == sieve_modes.TEST
                        else "",
                        "host": socket.gethostname(),
                    }
                }
            },
        }
    }

    # Write test result under sieve_test_result directory
    result_filename = "{}/{}-{}-{}.json".format(
        test_context.result_root_dir,
        test_context.controller,
        test_context.test_workload,
        os.path.basename(test_context.original_test_plan),
    )
    if not os.path.exists(os.path.dirname(result_filename)):
        try:
            os.makedirs(os.path.dirname(result_filename))
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

    with open(result_filename, "w") as test_result_json:
        json.dump(
            result_map,
            test_result_json,
            indent=4,
        )


def create_configmap(test_plan):
    test_plan_content = open(test_plan).read()
    configmap = {}
    configmap["apiVersion"] = "v1"
    configmap["kind"] = "ConfigMap"
    configmap["metadata"] = {"name": "sieve-testing-global-config"}
    configmap["data"] = {"sieveTestPlan": test_plan_content}
    configmap_path = "{}-configmap.yaml".format(test_plan[:-5])
    yaml.dump(configmap, open(configmap_path, "w"), sort_keys=False)
    return configmap_path


def create_kind_config(num_apiservers, num_workers):
    kind_config_dir = "kind_configs"
    os.makedirs(kind_config_dir, exist_ok=True)
    kind_config_filename = os.path.join(
        kind_config_dir,
        "kind-{}a-{}w.yaml".format(
            str(num_apiservers),
            str(num_workers),
        ),
    )
    with open(kind_config_filename, "w") as kind_config_file:
        kind_config_file.writelines(
            ["kind: Cluster\n", "apiVersion: kind.x-k8s.io/v1alpha4\n", "nodes:\n"]
        )
        for i in range(num_apiservers):
            kind_config_file.write("- role: control-plane\n")
        for i in range(num_workers):
            kind_config_file.write("- role: worker\n")
    return kind_config_filename


def redirect_workers(test_context: TestContext):
    leading_api = test_context.common_config.leading_api
    for i in range(test_context.num_workers):
        worker = "kind-worker" + (str(i + 1) if i > 0 else "")
        os_system(
            "docker exec {} bash -c \"sed -i 's/kind-external-load-balancer/{}/g' /etc/kubernetes/kubelet.conf\"".format(
                worker, leading_api
            )
        )
        os_system('docker exec {} bash -c "systemctl restart kubelet"'.format(worker))


def redirect_kubectl():
    client = docker.from_env()
    cp_port = client.containers.get("kind-control-plane").attrs["NetworkSettings"][
        "Ports"
    ]["6443/tcp"][0]["HostPort"]
    balancer_port = client.containers.get("kind-external-load-balancer").attrs[
        "NetworkSettings"
    ]["Ports"]["6443/tcp"][0]["HostPort"]
    kube_config = os.getenv("KUBECONFIG")
    target_prefix = "    server: https://127.0.0.1:"
    fin = open(kube_config)
    data = fin.read()
    # print("Replace {} w {} in {}".format(balancer_port, cp_port, kube_config))
    data = data.replace(target_prefix + balancer_port, target_prefix + cp_port)
    fin.close()
    fin = open(kube_config, "w")
    fin.write(data)
    fin.close()


def get_apiserver_ports(num_api):
    client = docker.from_env()
    ports = []
    for i in range(num_api):
        container_name_prefix = "kind-control-plane"
        suffix = str(i + 1) if i > 0 else ""
        cp_port = client.containers.get(container_name_prefix + suffix).attrs[
            "NetworkSettings"
        ]["Ports"]["6443/tcp"][0]["HostPort"]
        ports.append(cp_port)
    return ports


def prepare_sieve_server(test_context: TestContext):
    if test_context.mode == sieve_modes.TEST:
        configured_field_key_mask_json = "configured_field_key_mask.json"
        configured_field_path_mask_json = "configured_field_path_mask.json"
        json.dump(
            test_context.common_config.field_key_mask,
            open(configured_field_key_mask_json, "w"),
            indent=4,
            sort_keys=True,
        )
        json.dump(
            test_context.common_config.field_path_mask,
            open(configured_field_path_mask_json, "w"),
            indent=4,
            sort_keys=True,
        )
        learned_mask = os.path.join(test_context.oracle_dir, "mask.json")
        shutil.move(
            configured_field_key_mask_json,
            "sieve_server/{}".format(configured_field_key_mask_json),
        )
        shutil.move(
            configured_field_path_mask_json,
            "sieve_server/{}".format(configured_field_path_mask_json),
        )
        shutil.copy(learned_mask, "sieve_server/learned_field_path_mask.json")
    shutil.copy(test_context.test_plan, "sieve_server/server.yaml")
    org_dir = os.getcwd()
    os.chdir("sieve_server")
    os_system("go mod tidy")
    # TODO: we should build a container image for sieve server.
    os_system("env GOOS=linux GOARCH=amd64 go build")
    os.chdir(org_dir)
    os_system("docker cp sieve_server kind-control-plane:/sieve_server")


def start_sieve_server(test_context: TestContext):
    sieve_server_mode = (
        test_context.mode
        if test_context.mode == sieve_modes.TEST
        else sieve_modes.LEARN
    )
    os_system(
        "docker exec kind-control-plane bash -c 'cd /sieve_server && ./sieve-server {} &> sieve-server.log &'".format(
            sieve_server_mode
        )
    )


def stop_sieve_server():
    os_system("docker exec kind-control-plane bash -c 'pkill sieve-server'")


def setup_kind_cluster(test_context: TestContext):
    kind_config = create_kind_config(
        test_context.num_apiservers, test_context.num_workers
    )
    platform = ""
    if sys.platform == "darwin":
        platform = "macos-"
    k8s_container_registry = test_context.container_registry
    k8s_image_tag = (
        test_context.controller_config.kubernetes_version + "-" + platform + test_context.image_tag
    )
    retry_cnt = 0
    # Retry cluster creation for 5 times.
    while retry_cnt < 5:
        try:
            os_system("kind delete cluster")
            # Sleep here in case if the machine is slow and kind cluster deletion is not done before creating a new cluster.
            time.sleep(10 * retry_cnt)
            if retry_cnt == 0:
                print("Trying to create kind cluster")
            else:
                print(
                    "Retrying to create kind cluster; retry count {}".format(retry_cnt)
                )
            retry_cnt += 1
            os_system(
                "kind create cluster --image {}/node:{} --config {}".format(
                    k8s_container_registry, k8s_image_tag, kind_config
                )
            )
            os_system(
                "docker exec kind-control-plane bash -c 'mkdir -p /root/.kube/ && cp /etc/kubernetes/admin.conf /root/.kube/config'"
            )
            return
        except Exception:
            print(traceback.format_exc())


def setup_cluster(test_context: TestContext):
    """
    Set up the kind cluster for testing and wait until the control plane is ready.
    """
    setup_kind_cluster(test_context)
    print("\n\n")

    # When testing stale-state, we need to pause the apiserver
    # if workers talks to the paused apiserver, the whole cluster will be slowed down.
    # In a multi-apiserver set up (HA mode), each worker (kubelet) talks to a load balancer
    # which might forward the request to any backend apiserver.
    # We want to focus on testing how the controller handles staleness
    # so here we redirect the workers to an apiserver (configurable in config.json)
    # which Sieve will NOT slow down later.
    if "reconnectController" in test_context.action_types:
        cprint(
            "Redirecting workers and kubectl to the leading API server...",
            bcolors.OKGREEN,
        )
        redirect_workers(test_context)  # Redirect the kubelet on each worker node.
        redirect_kubectl()  # Redirect the local kubectl.
        ok("Redirection done")

    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()

    # Then we wait apiservers to be ready.
    print("Waiting for apiservers to be ready...")
    apiserver_list = []
    for i in range(test_context.num_apiservers):
        apiserver_name = "kube-apiserver-kind-control-plane" + (
            "" if i == 0 else str(i + 1)
        )
        apiserver_list.append(apiserver_name)
    # TODO: this can be better replaced by a watch.
    for tick in range(600):
        created = core_v1.list_namespaced_pod(
            "kube-system", watch=False, label_selector="component=kube-apiserver"
        ).items
        if len(created) == len(apiserver_list) and len(created) == len(
            [item for item in created if item.status.phase == "Running"]
        ):
            break
        time.sleep(1)

    if test_context.mode != sieve_modes.VANILLA:
        # Start the Sieve server.
        # In learn mode, it will record the controller events used for generating test plans.
        # In test mode, it reads the test plan and injects fault accordingly.
        prepare_sieve_server(test_context)
        cprint("Setting up Sieve server...", bcolors.OKGREEN)
        start_sieve_server(test_context)
        ok("Sieve server set up")

    time.sleep(3)  # Ensure that every apiserver will see the configmap is created.

    # We store the test plan into a configmap and create this configmap
    # so that the instrumentation at the apiserver side can also read the test plan
    # (by examining each incoming confimap creation event).
    # This is a bit hacky.
    # TODO: find a more elegant way to communicate with the instrumented apiserver.
    configmap = create_configmap(test_context.test_plan)
    os_system("kubectl apply -f {}".format(configmap))

    # Preload controller image to kind nodes.
    # This makes it faster to start the controller.
    image = "{}/{}:{}".format(
        test_context.container_registry,
        test_context.controller,
        test_context.image_tag,
    )
    kind_load_cmd = "kind load docker-image {}".format(image)
    print("Loading image {} to kind nodes...".format(image))
    if os_system(kind_load_cmd, early_exit=False) != 0:
        print("Cannot load image {} locally, try to pull from remote".format(image))
        os_system("docker pull {}".format(image))
        os_system(kind_load_cmd)


def deploy_controller(test_context: TestContext):
    # Install csi driver if some controller needs it.
    if test_context.use_csi_driver:
        print("Installing csi provisioner...")
        org_dir = os.getcwd()
        os.chdir("sieve_aux/csi-driver")
        os_system("./install.sh")
        os.chdir(org_dir)

    deployment_file = test_context.controller_config.controller_deployment_file_path

    # Backup the provided deployment file.
    backup_deployment_file = deployment_file + ".bkp"
    shutil.copyfile(deployment_file, backup_deployment_file)

    # Modify the marked container_registry and image_tag in the deployment yaml.
    # TODO: there should be a better way to parameterize the deployment yaml file.
    fin = open(deployment_file)
    data = fin.read()
    data = data.replace("${SIEVE-DR}", test_context.container_registry)
    data = data.replace("${SIEVE-DT}", test_context.image_tag)
    fin.close()
    fin = open(deployment_file, "w")
    fin.write(data)
    fin.close()

    # Run the provided deploy script.
    org_dir = os.getcwd()
    os.chdir(deploy_directory(test_context))
    os_system("./deploy.sh")
    os.chdir(org_dir)

    # Restore deployment file for later use.
    shutil.copyfile(backup_deployment_file, deployment_file)
    os.remove(backup_deployment_file)


def start_controller(test_context: TestContext):
    """
    Deploy the controller and wait until the controller becomes ready
    """
    controller = test_context.controller
    num_apiservers = test_context.num_apiservers
    deploy_controller(test_context)

    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()

    # Wait for controller pod to be ready
    # TODO: this can be better replaced by a watch.
    print("Wait for the controller pod to be ready...")
    pod_ready = False
    for tick in range(600):
        controller_pod = core_v1.list_namespaced_pod(
            test_context.common_config.namespace,
            watch=False,
            label_selector="sievetag=" + controller,
        ).items
        if len(controller_pod) >= 1:
            if controller_pod[0].status.phase == "Running":
                pod_ready = True
                break
        time.sleep(1)
    if not pod_ready:
        fail("waiting for the controller pod to be ready")
        raise Exception("Wait timeout after 600 seconds")

    # Issue a get crd operation to each apiserver (i.e., addr)
    # to make sure the instrumentation at the apiserver side
    # can observe the crd change.
    # This is necessary because sometimes the instrumentation at the apiserver
    # side needs to talk to the Sieve server when certain changes happen to
    # the custom resource objects (depending on the test plan).
    apiserver_addr_list = []
    apiserver_ports = get_apiserver_ports(num_apiservers)
    for port in apiserver_ports:
        apiserver_addr_list.append("https://127.0.0.1:" + port)
    for addr in apiserver_addr_list:
        for crd in test_context.controller_config.custom_resource_definitions:
            os_system("kubectl get {} -s {} --ignore-not-found=true".format(crd, addr))


def run_workload(
    test_context: TestContext,
):
    """
    Deploy the controller and run the provided testing workload.
    """

    cprint("Deploying controller...", bcolors.OKGREEN)
    start_controller(test_context)
    ok("Controller deployed")

    # If there are multiple contains in the controller pod then we need to find the correct one.
    select_container_from_pod = (
        " -c {} ".format(test_context.controller_config.container_name)
        if test_context.controller_config.container_name is not None
        else ""
    )

    kubernetes.config.load_kube_config()
    pod_name = (
        kubernetes.client.CoreV1Api()
        .list_namespaced_pod(
            test_context.common_config.namespace,
            watch=False,
            label_selector="sievetag=" + test_context.controller,
        )
        .items[0]
        .metadata.name
    )
    # Stream the controller log to streamed-controller.log for debugging purpose.
    # If the controller crashes due to some panic, Sieve will report that by checking
    # the streamed log.
    streamed_log_file = open(
        os.path.join(test_context.result_dir, "streamed-controller.log"), "w+"
    )
    streaming = subprocess.Popen(
        "kubectl logs {} {} -f".format(pod_name, select_container_from_pod),
        stdout=streamed_log_file,
        stderr=streamed_log_file,
        shell=True,
        preexec_fn=os.setsid,
    )

    # Stream the apiserver log.
    # The apiserver log should contain the state changes (i.e., creation, deletion and update events)
    # during the test workload and the log content will be later used for
    # (1) generating differential oracles for learn mode and
    # (2) detecting errors (e.g., inconsistency in end states) for test mode.
    # TODO: Storing everything in a log is a bit hacky,
    # and it is better to save all the recorded state changes in a database during runtime,
    # if that does not hurt the performance too much.
    # Another alternative is to just watch all the objects using the local kubectl.
    streamed_api_server_log_file = open(
        os.path.join(test_context.result_dir, "apiserver1.log"), "w+"
    )
    streaming_api_server = subprocess.Popen(
        "kubectl logs kube-apiserver-kind-control-plane -n kube-system -f",
        stdout=streamed_api_server_log_file,
        stderr=streamed_api_server_log_file,
        shell=True,
        preexec_fn=os.setsid,
    )

    cprint("Running test workload...", bcolors.OKGREEN)
    test_command = "{} {} {}".format(
        test_context.controller_config.test_command,
        test_context.test_workload,
        os.path.join(test_context.result_dir, "workload.log"),
    )
    process = subprocess.Popen(test_command, shell=True)
    process.wait()

    pod_name = (
        kubernetes.client.CoreV1Api()
        .list_namespaced_pod(
            test_context.common_config.namespace,
            watch=False,
            label_selector="sievetag=" + test_context.controller,
        )
        .items[0]
        .metadata.name
    )

    # Also save the log of other apiservers (for multi-apiserver set up) for debugging purpose.
    for i in range(1, test_context.num_apiservers):
        apiserver_name = "kube-apiserver-kind-control-plane" + (
            "" if i == 0 else str(i + 1)
        )
        apiserver_log = "apiserver{}.log".format(str(i + 1))
        os_system(
            "kubectl logs {} -n kube-system > {}/{}".format(
                apiserver_name, test_context.result_dir, apiserver_log
            )
        )

    # Save the Sieve server log.
    # In learn mode, the Sieve server log contains the collected controller events
    # which will be used to generate test plans.
    if test_context.mode != sieve_modes.VANILLA:
        os_system(
            "docker cp kind-control-plane:/sieve_server/sieve-server.log {}/sieve-server.log".format(
                test_context.result_dir
            )
        )

    # Save the controller log as well mainly for debugging purpose.
    os_system(
        "kubectl logs {} {} > {}/controller.log".format(
            pod_name, select_container_from_pod, test_context.result_dir
        )
    )
    # Stop streaming controller log.
    try:
        os.killpg(streaming.pid, signal.SIGTERM)
    except Exception as e:
        print("Unable to kill controller log streaming process: ", e)
    streamed_log_file.close()
    # Stop streaming apiserver log.
    os.killpg(streaming_api_server.pid, signal.SIGTERM)
    streamed_api_server_log_file.close()

    if test_context.mode != sieve_modes.VANILLA:
        stop_sieve_server()


def save_history_and_end_state(test_context: TestContext):
    """
    Generate three files:
    (1) a list of controller related objects (e.g., the controller pod) which will not be considered when applying differential oracles
    because the injected fault (e.g., controller crash) directly affects their states.
    (2) the entire history, including all the creation, deletion and update events, during the test workload,
    which is used for generating and applying differential oracles.
    (3) the end state after the test workload, which is used for generating and applying differential oracles.
    """
    save_controller_related_object_list(test_context)
    save_history(test_context)
    save_state(test_context)


def post_process(
    test_context: TestContext,
) -> TestResult:
    """
    Postprocess the collected logs and results.
    For learn mode, it will generate the test plan and differential oracles.
    For test mode, it will apply the differential oracles and report any detected errors.
    """
    if test_context.mode == sieve_modes.LEARN:
        if test_context.build_oracle:
            create_differential_oracles(test_context)
        analyze.generate_test_plans_from_learn_run(test_context)
        return None
    elif test_context.mode == sieve_modes.VANILLA:
        return None
    else:
        assert test_context.mode == sieve_modes.TEST
        test_result = check(test_context)
        print_error_and_debugging_info(test_context, test_result)
        return test_result


def teardown_cluster():
    os_system("kind delete cluster")


def save_previous_learn_results(test_context: TestContext):
    """
    Move the learn result to a differen folder.
    This should be only called in learn mode with build_oracle enabled.
    To build the differential oracles, we need to run the same workload twice
    to eliminate the non-determinism from the end state and state updates.
    """
    assert test_context.mode == sieve_modes.LEARN and test_context.build_oracle
    learn_res_dir = test_context.result_dir
    learn_prev_res_dir = first_pass_learn_result_dir(test_context.result_dir)
    assert os.path.isdir(
        learn_res_dir
    ), "{} should exist after first pass of learn run".format(learn_res_dir)
    print(
        "Moving the first pass learn result from {} to {}...".format(
            learn_res_dir, learn_prev_res_dir
        )
    )
    rmtree_if_exists(learn_prev_res_dir)
    shutil.move(learn_res_dir, learn_prev_res_dir)


def prepare_test_plan(test_context: TestContext):
    """
    Prepare the test plan.
    The test plan for test mode details what fault to inject and when to inject.
    The plans for learn and vanilla mode are rather simple:
    for learn mode, it only needs to contain the list of CRD to help filter out the irrevelant events;
    for vanilla mode it is empty.
    """
    # Clean this result dir if it exists
    rmtree_if_exists(test_context.result_dir)
    os.makedirs(test_context.result_dir)
    print("Sieve result dir: {}".format(test_context.result_dir))
    # Prepare the test plan for different modes
    if test_context.mode == sieve_modes.LEARN:
        # The plan for learn mode just contains the CRD list to fliter out events irrelevant to the controller
        print("Config for learn mode: {}".format(test_context.test_plan))
        create_plan_for_learn_mode(test_context)
    elif test_context.mode == sieve_modes.VANILLA:
        # The plan for vanilla mode is basically empty
        print("Config for vanilla mode: {}".format(test_context.test_plan))
        create_plan_for_vanilla_mode(test_context)
    else:
        # The test plan details what fault to inject and where to inject
        # and is generated by learn mode
        assert test_context.mode == sieve_modes.TEST
        print("Test plan: {}".format(test_context.test_plan))
        create_plan_for_test_mode(test_context)


def run_test(test_context: TestContext) -> TestResult:
    try:
        if test_context.postprocess:
            return post_process(test_context)
        prepare_test_plan(test_context)
        setup_cluster(test_context)
        run_workload(test_context)
        teardown_cluster()
        save_history_and_end_state(test_context)
        # if the build_oracle is enabled, then we need to run the learn run again
        # to eliminate nondeterminism in the end-state and state-update collected by Sieve
        if test_context.mode == sieve_modes.LEARN and test_context.build_oracle:
            print(
                "\nTo build the differential oracle, we need to run the learn run twice"
            )
            print("Starting the second learn run...")
            save_previous_learn_results(test_context)
            prepare_test_plan(test_context)
            setup_cluster(test_context)
            run_workload(test_context)
            teardown_cluster()
            save_history_and_end_state(test_context)
        return post_process(test_context)
    except Exception:
        print(traceback.format_exc())
        return TestResult(
            injection_completed=False,
            workload_completed=False,
            common_errors=[],
            end_state_errors=[],
            history_errors=[],
            no_exception=False,
            exception_message=traceback.format_exc(),
        )


def create_plan_for_test_mode(test_context: TestContext):
    test_plan_content = yaml.load(open(test_context.original_test_plan))
    # TODO: we should probably just add the annotatedReconcileStackFrame when generating the test plan.
    test_plan_content["annotatedReconcileStackFrame"] = [
        i for i in test_context.controller_config.annotated_reconcile_functions.values()
    ]
    yaml.dump(test_plan_content, open(test_context.test_plan, "w"), sort_keys=False)


def create_plan_for_learn_mode(test_context: TestContext):
    crd_list = test_context.controller_config.custom_resource_definitions
    learn_plan_content = {}
    # NOTE: we use the CRD list to focus on recording the events relevant to the controller during learn run
    # Here we assume all the relevant events are related to the CR objects or their owned objects
    # TODO: support customized defintion of "relevant events"
    learn_plan_content["crdList"] = crd_list
    # NOTE: rateLimiterEnabled is deprecated, will remove later
    learn_plan_content["rateLimiterEnabled"] = False
    learn_plan_content["rateLimiterInterval"] = 3
    learn_plan_content["annotatedReconcileStackFrame"] = [
        i for i in test_context.controller_config.annotated_reconcile_functions.values()
    ]
    yaml.dump(learn_plan_content, open(test_context.test_plan, "w"), sort_keys=False)


def create_plan_for_vanilla_mode(test_context: TestContext):
    vanilla_plan_content = {}
    yaml.dump(vanilla_plan_content, open(test_context.test_plan, "w"), sort_keys=False)


def get_test_workload_from_test_plan(test_plan_file):
    test_plan = yaml.safe_load(open(test_plan_file))
    return test_plan["workload"]


def generate_testing_cluster_config(mode, controller_config, test_plan, test_workload):
    num_apiservers = 1
    num_workers = 2
    use_csi_driver = False

    if test_workload in controller_config.test_setting:
        if "num_apiservers" in controller_config.test_setting[test_workload]:
            num_apiservers = controller_config.test_setting[test_workload][
                "num_apiservers"
            ]
        if "num_workers" in controller_config.test_setting[test_workload]:
            num_workers = controller_config.test_setting[test_workload]["num_workers"]
        if "use_csi_driver" in controller_config.test_setting[test_workload]:
            use_csi_driver = controller_config.test_setting[test_workload][
                "use_csi_driver"
            ]
    return (
        num_apiservers,
        num_workers,
        use_csi_driver,
    )


def run(
    controller_config_dir,
    test_workload,
    result_root_dir,
    mode,
    test_plan,
    container_registry,
    postprocess,
    build_oracle,
):
    """
    Prepare the test context based on the input options and the configurations
    and start to run the test.
    """
    controller_config = load_controller_config(controller_config_dir)
    if test_workload is None:
        assert mode == sieve_modes.TEST
        test_workload = get_test_workload_from_test_plan(test_plan)
        print("Get test workload {} from test plan".format(test_workload))
    num_apiservers, num_workers, use_csi_driver = generate_testing_cluster_config(
        mode, controller_config, test_plan, test_workload
    )
    oracle_dir = os.path.join(controller_config_dir, "oracle", test_workload)
    assert (
        os.path.isdir(oracle_dir)
        or (mode == sieve_modes.LEARN and build_oracle)
        or mode == sieve_modes.VANILLA
    ), "The oracle dir: {} must exist unless (1) you are running vanilla mode or (2) build_oracle is enabled".format(
        oracle_dir
    )
    os.makedirs(oracle_dir, exist_ok=True)
    if mode == sieve_modes.TEST:
        result_dir = os.path.join(
            result_root_dir,
            controller_config.controller_name,
            test_workload,
            mode,
            os.path.splitext(os.path.basename(test_plan))[0],
        )
    else:
        result_dir = os.path.join(
            result_root_dir,
            controller_config.controller_name,
            test_workload,
            mode,
        )

    image_tag = mode
    test_plan_to_run = os.path.join(result_dir, os.path.basename(test_plan))
    # Prepare the context for testing the controller
    test_context = TestContext(
        controller=controller_config.controller_name,
        controller_config_dir=controller_config_dir,
        test_workload=test_workload,
        mode=mode,
        postprocess=postprocess,
        build_oracle=build_oracle,
        original_test_plan=test_plan,
        test_plan=test_plan_to_run,
        result_root_dir=result_root_dir,
        result_dir=result_dir,
        oracle_dir=oracle_dir,
        container_registry=container_registry,
        image_tag=image_tag,
        num_apiservers=num_apiservers,
        num_workers=num_workers,
        use_csi_driver=use_csi_driver,
        common_config=common_config,
        controller_config=controller_config,
    )
    test_result = run_test(test_context)
    return test_result, test_context


def run_batch(
    controller,
    test_workload,
    dir,
    mode,
    test_plan_folder,
    docker,
    postprocess,
    build_oracle,
):
    """
    Run multiple test plans in the test_plan_folder in a batch.
    """
    assert mode == sieve_modes.TEST, "batch mode only allowed in test mode for now"
    assert os.path.isdir(test_plan_folder), "{} should be a folder".format(
        test_plan_folder
    )
    test_plans = glob.glob(os.path.join(test_plan_folder, "*.yaml"))
    # test_plans.sort(key=lambda test_plan: test_plan.split("-")[-1].split(".")[0])
    print("Test plans to run:")
    print("\n".join(test_plans))
    for test_plan in test_plans:
        start_time = time.time()
        test_result, test_context = run(
            controller,
            test_workload,
            dir,
            mode,
            test_plan,
            docker,
            postprocess,
            build_oracle,
        )
        save_run_result(
            test_context,
            test_result,
            start_time,
        )


if __name__ == "__main__":
    start_time = time.time()
    common_config = get_common_config()
    usage = "usage: python3 sieve.py [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option(
        "-c",
        "--controller_config_dir",
        dest="controller_config_dir",
        help="specify the CONTROLLER_CONFIG_DIR",
        metavar="CONTROLLER_CONFIG_DIR",
    )
    parser.add_option(
        "-w",
        "--test_workload",
        dest="test_workload",
        help="specify TEST_WORKLOAD to run",
        metavar="TEST_WORKLOAD",
    )
    parser.add_option(
        "-d",
        "--dir",
        dest="dir",
        help="save results to DIR",
        metavar="DIR",
    )
    parser.add_option(
        "-m",
        "--mode",
        dest="mode",
        help="MODE: vanilla, test, learn",
        metavar="MODE",
    )
    parser.add_option(
        "-p",
        "--test_plan",
        dest="test_plan",
        help="TEST_PLAN to execute",
        metavar="TEST_PLAN",
    )
    parser.add_option(
        "-r",
        "--registry",
        dest="registry",
        help="the container REGISTRY to pull the images from",
        metavar="REGISTRY",
        default=common_config.container_registry,
    )
    parser.add_option(
        "-b",
        "--batch",
        dest="batch",
        action="store_true",
        help="batch mode or not",
        default=False,
    )
    parser.add_option(
        "--postprocess",
        dest="postprocess",
        action="store_true",
        help="run postprocess only: report bugs for test mode, generate test plans for learn mode",
        default=False,
    )
    parser.add_option(
        "--build-oracle",
        dest="build_oracle",
        action="store_true",
        help="build the oracle by running learn twice",
        default=False,
    )

    (options, args) = parser.parse_args()

    if options.controller_config_dir is None:
        parser.error("parameter controller required")

    if options.mode == sieve_modes.LEARN:
        options.test_plan = "learn.yaml"
        if options.dir is None:
            options.dir = "sieve_learn_results"
    elif options.mode == sieve_modes.VANILLA:
        options.test_plan = "vanilla.yaml"
        if options.dir is None:
            options.dir = "sieve_vanilla_results"
    else:
        if options.dir is None:
            options.dir = "sieve_test_results"
        if options.test_plan is None:
            parser.error("parameter test_plan required in test mode")

    if options.test_workload is None:
        if options.mode != sieve_modes.TEST:
            parser.error("parameter test required in learn and vanilla mode")

    if options.mode != sieve_modes.LEARN and options.build_oracle:
        parser.error("parameter build_oracle cannot be enabled when mode is not learn")

    if options.postprocess and options.build_oracle:
        parser.error(
            "parameter postprocess cannot be enabled when build_oracle is enabled"
        )

    print("Running Sieve with mode: {}...".format(options.mode))

    if options.batch:
        run_batch(
            options.controller_config_dir,
            options.test_workload,
            options.dir,
            options.mode,
            options.test_plan,
            options.registry,
            options.postprocess,
            options.build_oracle,
        )
    else:
        test_result, test_context = run(
            options.controller_config_dir,
            options.test_workload,
            options.dir,
            options.mode,
            options.test_plan,
            options.registry,
            options.postprocess,
            options.build_oracle,
        )

        save_run_result(
            test_context,
            test_result,
            start_time,
        )
    print("Total time: {} seconds".format(time.time() - start_time))
