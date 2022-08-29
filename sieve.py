import shutil
from typing import Tuple
import docker
import optparse
import os
import kubernetes
from sieve_common.default_config import (
    get_common_config,
    get_controller_config,
)
import time
import json
import glob
from sieve_analyzer import analyze
from sieve_oracle.oracle import (
    persist_state,
    persist_history,
    generate_controller_family,
    canonicalize_history_and_state,
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
    cmd_early_exit,
    deploy_directory,
)


def save_run_result(
    test_context: TestContext,
    test_result: TestResult,
    start_time,
):
    if test_context.mode != sieve_modes.TEST:
        return

    if test_result is None:
        return

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

    # Testing mode, write test result under sieve_test_result directory
    result_filename = "sieve_test_results/{}-{}-{}.json".format(
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


def watch_crd(crds, addrs):
    for addr in addrs:
        for crd in crds:
            cmd_early_exit("kubectl get %s -s %s --ignore-not-found=true" % (crd, addr))


def generate_configmap(test_plan):
    test_plan_content = open(test_plan).read()
    configmap = {}
    configmap["apiVersion"] = "v1"
    configmap["kind"] = "ConfigMap"
    configmap["metadata"] = {"name": "sieve-testing-global-config"}
    configmap["data"] = {"sieveTestPlan": test_plan_content}
    configmap_path = "%s-configmap.yaml" % test_plan[:-5]
    yaml.dump(configmap, open(configmap_path, "w"), sort_keys=False)
    return configmap_path


def generate_kind_config(num_apiservers, num_workers):
    kind_config_dir = "kind_configs"
    os.makedirs(kind_config_dir, exist_ok=True)
    kind_config_filename = os.path.join(
        kind_config_dir,
        "kind-%sa-%sw.yaml"
        % (
            str(num_apiservers),
            str(num_workers),
        ),
    )
    kind_config_file = open(kind_config_filename, "w")
    kind_config_file.writelines(
        ["kind: Cluster\n", "apiVersion: kind.x-k8s.io/v1alpha4\n", "nodes:\n"]
    )
    for i in range(num_apiservers):
        kind_config_file.write("- role: control-plane\n")
    for i in range(num_workers):
        kind_config_file.write("- role: worker\n")
    kind_config_file.close()
    return kind_config_filename


def redirect_workers(test_context: TestContext):
    leading_api = test_context.common_config.leading_api
    for i in range(test_context.num_workers):
        worker = "kind-worker" + (str(i + 1) if i > 0 else "")
        cmd_early_exit(
            "docker exec %s bash -c \"sed -i 's/kind-external-load-balancer/%s/g' /etc/kubernetes/kubelet.conf\""
            % (worker, leading_api)
        )
        cmd_early_exit('docker exec %s bash -c "systemctl restart kubelet"' % worker)


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
    print("replace %s w %s in %s" % (balancer_port, cp_port, kube_config))
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
        cmd_early_exit(
            "mv %s sieve_server/%s"
            % (configured_field_key_mask_json, configured_field_key_mask_json)
        )
        cmd_early_exit(
            "mv %s sieve_server/%s"
            % (configured_field_path_mask_json, configured_field_path_mask_json)
        )
        cmd_early_exit("cp %s sieve_server/learned_field_path_mask.json" % learned_mask)
    cmd_early_exit("cp %s sieve_server/server.yaml" % test_context.test_plan)
    org_dir = os.getcwd()
    os.chdir("sieve_server")
    cmd_early_exit("go mod tidy")
    # TODO: we should build a container image for sieve server
    cmd_early_exit("env GOOS=linux GOARCH=amd64 go build")
    os.chdir(org_dir)
    cmd_early_exit("docker cp sieve_server kind-control-plane:/sieve_server")


def start_sieve_server(test_context: TestContext):
    sieve_server_mode = (
        test_context.mode
        if test_context.mode == sieve_modes.TEST
        else sieve_modes.LEARN
    )
    cmd_early_exit(
        "docker exec kind-control-plane bash -c 'cd /sieve_server && ./sieve-server %s &> sieve-server.log &'"
        % sieve_server_mode
    )


def stop_sieve_server():
    cmd_early_exit("docker exec kind-control-plane bash -c 'pkill sieve-server'")


def setup_kind_cluster(test_context: TestContext):
    kind_config = generate_kind_config(
        test_context.num_apiservers, test_context.num_workers
    )
    k8s_container_registry = test_context.container_registry
    k8s_image_tag = (
        test_context.controller_config.kubernetes_version + "-" + test_context.image_tag
    )
    retry_cnt = 0
    while retry_cnt < 5:
        try:
            cmd_early_exit("kind delete cluster")
            # sleep here in case if the machine is slow and kind cluster deletion is not done before creating a new cluster
            time.sleep(5 + 10 * retry_cnt)
            retry_cnt += 1
            print("try to create kind cluster; retry count {}".format(retry_cnt))
            cmd_early_exit(
                "kind create cluster --image %s/node:%s --config %s"
                % (k8s_container_registry, k8s_image_tag, kind_config)
            )
            cmd_early_exit(
                "docker exec kind-control-plane bash -c 'mkdir -p /root/.kube/ && cp /etc/kubernetes/admin.conf /root/.kube/config'"
            )
            return
        except Exception:
            print(traceback.format_exc())


def setup_cluster(test_context: TestContext):
    setup_kind_cluster(test_context)
    print("\n\n")

    cmd_early_exit("rm -rf %s" % test_context.result_dir)
    os.makedirs(test_context.result_dir)
    if (
        test_context.mode == sieve_modes.LEARN_ONCE
        or test_context.mode == sieve_modes.LEARN_TWICE
    ):
        print("Learn with: %s" % test_context.test_plan)
        generate_learn_plan(
            test_context.test_plan,
            test_context.controller_config.custom_resource_definitions,
        )
    elif test_context.mode == sieve_modes.VANILLA:
        print("Vanilla with: %s" % test_context.test_plan)
        generate_vanilla_plan(test_context.test_plan)
    else:
        assert test_context.mode == sieve_modes.TEST
        print("Test with: %s" % test_context.test_plan)
        cmd_early_exit(
            "cp %s %s" % (test_context.original_test_plan, test_context.test_plan)
        )

    # when testing stale-state, we need to pause the apiserver
    # if workers talks to the paused apiserver, the whole cluster will be slowed down
    # so we need to redirect the workers to other apiservers
    if "reconnectController" in test_context.action_types:
        cprint(
            "Redirecting workers and kubectl to the leading API server...",
            bcolors.OKGREEN,
        )
        redirect_workers(test_context)
        redirect_kubectl()
        ok("Redirection done")

    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()

    # Then we wait apiservers to be ready
    print("Waiting for apiservers to be ready...")
    apiserver_list = []
    for i in range(test_context.num_apiservers):
        apiserver_name = "kube-apiserver-kind-control-plane" + (
            "" if i == 0 else str(i + 1)
        )
        apiserver_list.append(apiserver_name)

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
        prepare_sieve_server(test_context)
        cprint("Setting up Sieve server...", bcolors.OKGREEN)
        start_sieve_server(test_context)
        ok("Sieve server set up")

    time.sleep(3)  # ensure that every apiserver will see the configmap is created
    configmap = generate_configmap(test_context.test_plan)
    cmd_early_exit("kubectl apply -f %s" % configmap)

    # Preload operator image to kind nodes
    image = "%s/%s:%s" % (
        test_context.container_registry,
        test_context.controller,
        test_context.image_tag,
    )
    kind_load_cmd = "kind load docker-image %s" % (image)
    print("Loading image %s to kind nodes..." % (image))
    if cmd_early_exit(kind_load_cmd, early_exit=False) != 0:
        print("Cannot load image %s locally, try to pull from remote" % (image))
        cmd_early_exit("docker pull %s" % (image))
        cmd_early_exit(kind_load_cmd)


def deploy_controller(test_context: TestContext):
    if test_context.use_csi_driver:
        print("Installing csi provisioner...")
        cmd_early_exit("cd sieve_aux/csi-driver && ./install.sh")

    deployment_file = test_context.controller_config.controller_deployment_file_path
    # backup deployment file
    backup_deployment_file = deployment_file + ".bkp"
    shutil.copyfile(deployment_file, backup_deployment_file)

    # modify container_registry and image_tag
    fin = open(deployment_file)
    data = fin.read()
    data = data.replace("${SIEVE-DR}", test_context.container_registry)
    data = data.replace("${SIEVE-DT}", test_context.image_tag)
    fin.close()
    fin = open(deployment_file, "w")
    fin.write(data)
    fin.close()

    # run the deploy script
    org_dir = os.getcwd()
    os.chdir(deploy_directory(test_context))
    cmd_early_exit("./deploy.sh")
    os.chdir(org_dir)

    # restore deployment file
    shutil.copyfile(backup_deployment_file, deployment_file)
    os.remove(backup_deployment_file)


def start_operator(test_context: TestContext):
    controller = test_context.controller
    num_apiservers = test_context.num_apiservers
    deploy_controller(test_context)

    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()

    # Wait for controller pod ready
    print("Wait for the operator pod to be ready...")
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
        fail("waiting for the operator pod to be ready")
        raise Exception("Wait timeout after 600 seconds")

    apiserver_addr_list = []
    apiserver_ports = get_apiserver_ports(num_apiservers)
    # print("apiserver ports", apiserver_ports)
    for port in apiserver_ports:
        apiserver_addr_list.append("https://127.0.0.1:" + port)
    watch_crd(
        test_context.controller_config.custom_resource_definitions, apiserver_addr_list
    )


def run_workload(
    test_context: TestContext,
) -> Tuple[int, str]:

    cprint("Deploying operator...", bcolors.OKGREEN)
    start_operator(test_context)
    ok("Operator deployed")

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
    streamed_log_file = open(
        os.path.join(test_context.result_dir, "streamed-operator.log"), "w+"
    )
    streaming = subprocess.Popen(
        "kubectl logs %s %s -f" % (pod_name, select_container_from_pod),
        stdout=streamed_log_file,
        stderr=streamed_log_file,
        shell=True,
        preexec_fn=os.setsid,
    )

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

    use_soft_timeout = "0"
    if "pauseController" in test_context.action_types:
        use_soft_timeout = "1"

    cprint("Running test workload...", bcolors.OKGREEN)
    test_command = "%s %s %s %s" % (
        test_context.controller_config.test_command,
        test_context.test_workload,
        use_soft_timeout,
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

    for i in range(1, test_context.num_apiservers):
        apiserver_name = "kube-apiserver-kind-control-plane" + (
            "" if i == 0 else str(i + 1)
        )
        apiserver_log = "apiserver%s.log" % (str(i + 1))
        cmd_early_exit(
            "kubectl logs %s -n kube-system > %s/%s"
            % (apiserver_name, test_context.result_dir, apiserver_log)
        )

    if test_context.mode != sieve_modes.VANILLA:
        cmd_early_exit(
            "docker cp kind-control-plane:/sieve_server/sieve-server.log %s/sieve-server.log"
            % (test_context.result_dir)
        )

    cmd_early_exit(
        "kubectl logs %s %s > %s/operator.log"
        % (pod_name, select_container_from_pod, test_context.result_dir)
    )
    os.killpg(streaming.pid, signal.SIGTERM)
    streamed_log_file.close()
    os.killpg(streaming_api_server.pid, signal.SIGTERM)
    streamed_api_server_log_file.close()

    if test_context.mode != sieve_modes.VANILLA:
        stop_sieve_server()


def check_result(
    test_context: TestContext,
) -> TestResult:
    generate_controller_family(test_context)
    persist_history(test_context)
    persist_state(test_context)
    if (
        test_context.mode == sieve_modes.LEARN_ONCE
        or test_context.mode == sieve_modes.LEARN_TWICE
    ):
        if test_context.mode == sieve_modes.LEARN_TWICE:
            canonicalize_history_and_state(test_context)
        analyze.analyze_trace(test_context)
        return None
    elif test_context.mode == sieve_modes.VANILLA:
        return None
    else:
        assert test_context.mode == sieve_modes.TEST
        test_result = check(test_context)
        print_error_and_debugging_info(test_context, test_result)
        return test_result


def run_test(test_context: TestContext) -> TestResult:
    try:
        if (
            test_context.phase == "all"
            or test_context.phase == "setup"
            or test_context.phase == "setup_workload"
        ):
            setup_cluster(test_context)
        if (
            test_context.phase == "all"
            or test_context.phase == "setup_workload"
            or test_context.phase == "workload"
            or test_context.phase == "workload_check"
        ):
            run_workload(test_context)
        if (
            test_context.phase == "all"
            or test_context.phase == "check"
            or test_context.phase == "workload_check"
        ):
            test_result = check_result(test_context)
            return test_result
        return None
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


def generate_learn_plan(learn_plan, crd_list):
    learn_plan_map = {}
    learn_plan_map["crdList"] = crd_list
    # hardcode rate limiter to disabled for now
    learn_plan_map["rateLimiterEnabled"] = False
    learn_plan_map["rateLimiterInterval"] = 3
    yaml.dump(learn_plan_map, open(learn_plan, "w"), sort_keys=False)


def generate_vanilla_plan(vanilla_plan):
    vanilla_plan_map = {}
    yaml.dump(vanilla_plan_map, open(vanilla_plan, "w"), sort_keys=False)


def get_test_workload_from_test_plan(test_plan_file):
    test_plan = yaml.safe_load(open(test_plan_file))
    return test_plan["workload"]


def run(
    controller,
    test_workload,
    log_dir,
    mode,
    test_plan,
    container_registry,
    phase="all",
):
    common_config = get_common_config()
    controller_config = get_controller_config(
        common_config.controller_folder, controller
    )
    num_apiservers = 1
    num_workers = 2
    use_csi_driver = False
    if test_workload is None:
        assert mode == sieve_modes.TEST
        test_workload = get_test_workload_from_test_plan(test_plan)
        print("get test workload {} from test plan".format(test_workload))
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
    oracle_dir = os.path.join(
        common_config.controller_folder, controller, "oracle", test_workload
    )
    os.makedirs(oracle_dir, exist_ok=True)
    result_dir = os.path.join(
        log_dir, controller, test_workload, mode, os.path.basename(test_plan)
    )
    print("Log dir: %s" % result_dir)
    image_tag = (
        sieve_modes.LEARN
        if mode == sieve_modes.LEARN_ONCE or mode == sieve_modes.LEARN_TWICE
        else mode
    )
    test_plan_to_run = os.path.join(result_dir, os.path.basename(test_plan))
    test_context = TestContext(
        controller=controller,
        test_workload=test_workload,
        mode=mode,
        phase=phase,
        original_test_plan=test_plan,
        test_plan=test_plan_to_run,
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


def run_batch(controller, test_workload, dir, mode, test_plan_folder, docker, phase):
    assert mode == sieve_modes.TEST, "batch mode only allowed in test mode"
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
            phase,
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
        "--controller",
        dest="controller",
        help="specify the CONTROLLER to test",
        metavar="CONTROLLER",
    )
    parser.add_option(
        "-w",
        "--test_workload",
        dest="test_workload",
        help="specify TEST_WORKLOAD to run",
        metavar="TEST_WORKLOAD",
    )
    parser.add_option(
        "-l", "--log", dest="log", help="save to LOG", metavar="LOG", default="log"
    )
    parser.add_option(
        "-m",
        "--mode",
        dest="mode",
        help="MODE: vanilla, test, learn-once, learn-twice",
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
        "--phase",
        dest="phase",
        help="run the PHASE: setup, workload, check or all",
        metavar="PHASE",
        default="all",
    )

    (options, args) = parser.parse_args()

    if options.controller is None:
        parser.error("parameter controller required")

    if (
        options.mode == sieve_modes.LEARN_ONCE
        or options.mode == sieve_modes.LEARN_TWICE
    ):
        options.test_plan = "learn.yaml"
    elif options.mode == sieve_modes.VANILLA:
        options.test_plan = "vanilla.yaml"
    else:
        if options.test_plan is None:
            parser.error("parameter test_plan required in test mode")

    if options.test_workload is None:
        if options.mode != sieve_modes.TEST:
            parser.error("parameter test required in learn and vanilla mode")

    if options.phase not in [
        "all",
        "setup",
        "workload",
        "check",
        "setup_workload",
        "workload_check",
    ]:
        parser.error("invalid phase option: %s" % options.phase)

    print("Running Sieve with mode: %s..." % options.mode)

    if options.batch:
        run_batch(
            options.controller,
            options.test_workload,
            options.log,
            options.mode,
            options.test_plan,
            options.registry,
            options.phase,
        )
    else:
        if options.mode == sieve_modes.LEARN_TWICE:
            # Run learn-once first
            run(
                options.controller,
                options.test_workload,
                options.log,
                sieve_modes.LEARN_ONCE,
                options.test_plan,
                options.registry,
                options.phase,
            )

        test_result, test_context = run(
            options.controller,
            options.test_workload,
            options.log,
            options.mode,
            options.test_plan,
            options.registry,
            options.phase,
        )

        save_run_result(
            test_context,
            test_result,
            start_time,
        )
    cmd_early_exit("kind delete cluster")
    print("Total time: {} seconds".format(time.time() - start_time))
