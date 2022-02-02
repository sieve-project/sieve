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
    canonicalize_history_and_state,
    generate_fatal,
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
    CONFIGURED_MASK,
    TestContext,
    cprint,
    bcolors,
    ok,
    fail,
    sieve_modes,
    cmd_early_exit,
    NO_ERROR_MESSAGE,
    sieve_stages,
    deploy_directory,
)


def save_run_result(
    project, test, mode, stage, test_config, ret_val, messages, start_time
):
    if stage != sieve_stages.TEST:
        return

    result_map = {
        project: {
            test: {
                mode: {
                    test_config: {
                        "duration": time.time() - start_time,
                        "ret_val": ret_val,
                        "messages": messages,
                        "test_config_content": open(test_config).read()
                        if mode != "vanilla"
                        else None,
                        "host": socket.gethostname(),
                    }
                }
            },
        }
    }

    # Testing mode, write test result under sieve_test_result directory
    result_filename = "sieve_test_results/{}-{}-{}.json".format(
        project, test, os.path.basename(test_config)
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


def generate_configmap(test_config):
    yaml_map = yaml.safe_load(open(test_config))
    configmap = {}
    configmap["apiVersion"] = "v1"
    configmap["kind"] = "ConfigMap"
    configmap["metadata"] = {"name": "sieve-testing-global-config"}
    configmap["data"] = {}
    for key in yaml_map:
        if isinstance(yaml_map[key], list):
            assert key.endswith("-list")
            configmap["data"]["SIEVE-" + key.upper()] = ",".join(yaml_map[key])
        else:
            configmap["data"]["SIEVE-" + key.upper()] = yaml_map[key]
    configmap_path = "%s-configmap.yaml" % test_config[:-5]
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
    if (
        test_context.stage == sieve_stages.TEST
        and test_context.mode != sieve_modes.VANILLA
    ):
        configured_mask = "configured-mask.json"
        configured_mask_map = {
            "keys": [path[3:] for path in CONFIGURED_MASK if path.startswith("**/")],
            "paths": [path for path in CONFIGURED_MASK if not path.startswith("**/")],
        }
        json.dump(
            configured_mask_map, open(configured_mask, "w"), indent=4, sort_keys=True
        )
        learned_mask = os.path.join(test_context.oracle_dir, "mask.json")
        cmd_early_exit("mv %s sieve_server/configured-mask.json" % configured_mask)
        cmd_early_exit("cp %s sieve_server/learned-mask.json" % learned_mask)
    cmd_early_exit("cp %s sieve_server/server.yaml" % test_context.test_config)
    org_dir = os.getcwd()
    os.chdir("sieve_server")
    cmd_early_exit("go mod tidy")
    # TODO: we should build a container image for sieve server
    cmd_early_exit("env GOOS=linux GOARCH=amd64 go build")
    os.chdir(org_dir)
    cmd_early_exit("docker cp sieve_server kind-control-plane:/sieve_server")


def start_sieve_server():
    cmd_early_exit(
        "docker exec kind-control-plane bash -c 'cd /sieve_server && ./sieve-server &> sieve-server.log &'"
    )


def stop_sieve_server():
    cmd_early_exit("docker exec kind-control-plane bash -c 'pkill sieve-server'")


def setup_kind_cluster(test_context: TestContext):
    kind_config = generate_kind_config(
        test_context.num_apiservers, test_context.num_workers
    )
    k8s_docker_repo = test_context.docker_repo
    k8s_docker_tag = (
        test_context.controller_config.kubernetes_version
        + "-"
        + test_context.docker_tag
    )

    cmd_early_exit(
        "kind create cluster --image %s/node:%s --config %s"
        % (k8s_docker_repo, k8s_docker_tag, kind_config)
    )
    cmd_early_exit(
        "docker exec kind-control-plane bash -c 'mkdir -p /root/.kube/ && cp /etc/kubernetes/admin.conf /root/.kube/config'"
    )


def setup_cluster(test_context: TestContext):
    cmd_early_exit("kind delete cluster")
    # sleep here in case if the machine is slow and deletion is not done before creating a new cluster
    time.sleep(5)
    setup_kind_cluster(test_context)
    print("\n\n")

    prepare_sieve_server(test_context)

    # when testing stale-state, we need to pause the apiserver
    # if workers talks to the paused apiserver, the whole cluster will be slowed down
    # so we need to redirect the workers to other apiservers
    if test_context.mode == sieve_modes.STALE_STATE:
        redirect_workers(test_context)
        redirect_kubectl()

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

    time.sleep(3)  # ensure that every apiserver will see the configmap is created
    configmap = generate_configmap(test_context.test_config)
    cmd_early_exit("kubectl apply -f %s" % configmap)

    # Preload operator image to kind nodes
    image = "%s/%s:%s" % (
        test_context.docker_repo,
        test_context.project,
        test_context.docker_tag,
    )
    kind_load_cmd = "kind load docker-image %s" % (image)
    print("Loading image %s to kind nodes..." % (image))
    if cmd_early_exit(kind_load_cmd, early_exit=False) != 0:
        print("Cannot load image %s locally, try to pull from remote" % (image))
        cmd_early_exit("docker pull %s" % (image))
        cmd_early_exit(kind_load_cmd)

    # csi driver can only work with one apiserver so it cannot be enabled in stale state mode
    if test_context.mode != sieve_modes.STALE_STATE and test_context.use_csi_driver:
        print("Installing csi provisioner...")
        cmd_early_exit("cd sieve_aux/csi-driver && ./install.sh")


def deploy_controller(test_context: TestContext):
    deployment_file = test_context.controller_config.controller_deployment_file_path
    # backup deployment file
    backup_deployment_file = deployment_file + ".bkp"
    shutil.copyfile(deployment_file, backup_deployment_file)

    # modify docker_repo and docker_tag
    fin = open(deployment_file)
    data = fin.read()
    data = data.replace("${SIEVE-DR}", test_context.docker_repo)
    data = data.replace("${SIEVE-DT}", test_context.docker_tag)
    fin.close()
    fin = open(deployment_file, "w")
    fin.write(data)
    fin.close()

    # run the deploy script
    org_dir = os.getcwd()
    os.chdir(deploy_directory(test_context.project))
    cmd_early_exit("./deploy.sh")
    os.chdir(org_dir)

    # restore deployment file
    shutil.copyfile(backup_deployment_file, deployment_file)
    os.remove(backup_deployment_file)


def start_operator(test_context: TestContext):
    project = test_context.project
    num_apiservers = test_context.num_apiservers
    deploy_controller(test_context)

    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()

    # Wait for project pod ready
    print("Wait for the operator pod to be ready...")
    pod_ready = False
    for tick in range(600):
        project_pod = core_v1.list_namespaced_pod(
            test_context.common_config.namespace,
            watch=False,
            label_selector="sievetag=" + project,
        ).items
        if len(project_pod) >= 1:
            if project_pod[0].status.phase == "Running":
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
    if test_context.mode != sieve_modes.VANILLA:
        cprint("Setting up Sieve server...", bcolors.OKGREEN)
        start_sieve_server()
        ok("Sieve server set up")

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
            label_selector="sievetag=" + test_context.project,
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

    cprint("Running test workload...", bcolors.OKGREEN)
    test_command = "%s %s %s %s" % (
        test_context.controller_config.test_command,
        test_context.test_name,
        test_context.mode,
        os.path.join(test_context.result_dir, "workload.log"),
    )
    process = subprocess.Popen(test_command, shell=True)
    process.wait()

    pod_name = (
        kubernetes.client.CoreV1Api()
        .list_namespaced_pod(
            test_context.common_config.namespace,
            watch=False,
            label_selector="sievetag=" + test_context.project,
        )
        .items[0]
        .metadata.name
    )

    for i in range(test_context.num_apiservers):
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
    if test_context.mode != sieve_modes.VANILLA:
        stop_sieve_server()
    # TODO: we should get the state from apiserver log and move it to check_result
    persist_state(test_context)


def check_result(
    test_context: TestContext,
) -> Tuple[int, str]:
    if test_context.stage == sieve_stages.LEARN:
        persist_history(test_context)
        if test_context.mode == sieve_modes.LEARN_TWICE:
            canonicalize_history_and_state(test_context)
        analyze.analyze_trace(test_context)
        return 0, NO_ERROR_MESSAGE
    else:
        if test_context.mode == sieve_modes.VANILLA:
            return 0, NO_ERROR_MESSAGE
        ret_val, messages = check(test_context)
        open(os.path.join(test_context.result_dir, "bug-report.txt"), "w").write(
            messages
        )
        return ret_val, messages


def run_test(test_context: TestContext) -> Tuple[int, str]:
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
            ret_val, messages = check_result(test_context)
            return ret_val, messages
        return 0, NO_ERROR_MESSAGE
    except Exception:
        print(traceback.format_exc())
        return -4, generate_fatal(traceback.format_exc())


def generate_learn_config(
    namespace, learn_config, mode, rate_limiter_enabled, crd_list
):
    learn_config_map = {}
    learn_config_map["stage"] = sieve_stages.LEARN
    learn_config_map["mode"] = mode
    learn_config_map["namespace"] = namespace
    learn_config_map["crd-list"] = crd_list
    if rate_limiter_enabled:
        learn_config_map["rate-limiter-enabled"] = "true"
        print("Turn on rate limiter")
    else:
        learn_config_map["rate-limiter-enabled"] = "false"
        print("Turn off rate limiter")
    # hardcode the interval to 3 seconds for now
    learn_config_map["rate-limiter-interval"] = "3"
    yaml.dump(learn_config_map, open(learn_config, "w"), sort_keys=False)


def generate_vanilla_config(vanilla_config):
    vanilla_config_map = {}
    vanilla_config_map["stage"] = sieve_stages.TEST
    vanilla_config_map["mode"] = sieve_modes.NONE
    yaml.dump(vanilla_config_map, open(vanilla_config, "w"), sort_keys=False)


def run(
    project,
    test,
    log_dir,
    mode,
    stage,
    config,
    docker_repo,
    rate_limiter_enabled=False,
    phase="all",
):
    common_config = get_common_config()
    controller_config = get_controller_config(project)
    num_apiservers = 1
    num_workers = 2
    use_csi_driver = False
    if test in controller_config.test_setting:
        if "num_apiservers" in controller_config.test_setting[test]:
            num_apiservers = controller_config.test_setting[test]["num_apiservers"]
        if "num_workers" in controller_config.test_setting[test]:
            num_workers = controller_config.test_setting[test]["num_workers"]
        if "use_csi_driver" in controller_config.test_setting[test]:
            use_csi_driver = controller_config.test_setting[test]["use_csi_driver"]
    if mode == sieve_modes.STALE_STATE and num_apiservers < 3:
        num_apiservers = 3
    elif use_csi_driver:
        num_apiservers = 1
        num_workers = 0
    oracle_dir = os.path.join("examples", project, "oracle", test)
    os.makedirs(oracle_dir, exist_ok=True)
    result_dir = os.path.join(
        log_dir, project, test, stage, mode, os.path.basename(config)
    )
    print("Log dir: %s" % result_dir)
    if phase == "all" or phase == "setup" or phase == "setup_workload":
        cmd_early_exit("rm -rf %s" % result_dir)
        os.makedirs(result_dir, exist_ok=True)
    docker_tag = stage if stage == sieve_stages.LEARN else mode
    config_to_use = os.path.join(result_dir, os.path.basename(config))
    if stage == sieve_stages.LEARN:
        print("Learning stage with config: %s" % config_to_use)
        generate_learn_config(
            common_config.namespace,
            config_to_use,
            sieve_stages.LEARN,
            rate_limiter_enabled,
            controller_config.custom_resource_definitions,
        )
    else:
        print("Testing stage with config: %s" % config_to_use)
        if mode == sieve_modes.VANILLA:
            generate_vanilla_config(config_to_use)
        else:
            cmd_early_exit("cp %s %s" % (config, config_to_use))
    test_context = TestContext(
        project=project,
        test_name=test,
        stage=stage,
        mode=mode,
        phase=phase,
        test_config=config_to_use,
        result_dir=result_dir,
        oracle_dir=oracle_dir,
        docker_repo=docker_repo,
        docker_tag=docker_tag,
        num_apiservers=num_apiservers,
        num_workers=num_workers,
        use_csi_driver=use_csi_driver,
        common_config=common_config,
        controller_config=controller_config,
    )
    ret_val, messages = run_test(test_context)
    if ret_val != -4:
        print_error_and_debugging_info(test_context, ret_val, messages)
    return ret_val, messages


def run_batch(project, test, dir, mode, stage, docker):
    assert stage == sieve_stages.TEST, "can only run batch mode in test stage"
    config_dir = os.path.join(
        "log", project, test, sieve_stages.LEARN, sieve_modes.LEARN_ONCE, mode
    )
    configs = glob.glob(os.path.join(config_dir, "*.yaml"))
    configs.sort(key=lambda config: config.split("-")[-1].split(".")[0])
    print("Configs to test:")
    print("\n".join(configs))
    for config in configs:
        start_time = time.time()
        ret_val, report = run(
            project,
            test,
            dir,
            mode,
            stage,
            config,
            docker,
        )
        save_run_result(
            project,
            test,
            mode,
            stage,
            config,
            ret_val,
            report,
            start_time,
        )


if __name__ == "__main__":
    start_time = time.time()
    common_config = get_common_config()
    usage = "usage: python3 sieve.py [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option(
        "-p",
        "--project",
        dest="project",
        help="specify PROJECT to test",
        metavar="PROJECT",
    )
    parser.add_option(
        "-t",
        "--test",
        dest="test",
        help="specify TEST to run",
        metavar="TEST",
    )
    parser.add_option(
        "-d",
        "--docker",
        dest="docker",
        help="DOCKER repo that you have access",
        metavar="DOCKER",
        default=common_config.docker_registry,
    )
    parser.add_option(
        "-l", "--log", dest="log", help="save to LOG", metavar="LOG", default="log"
    )
    parser.add_option(
        "-m",
        "--mode",
        dest="mode",
        help="test MODE: vanilla, stale-state, unobserved-state, intermediate-state",
        metavar="MODE",
    )
    parser.add_option(
        "-c",
        "--config",
        dest="config",
        help="test CONFIG",
        metavar="CONFIG",
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
    parser.add_option(
        "-s",
        "--stage",
        dest="stage",
        help="STAGE: learn, test",
    )
    parser.add_option(
        "-r",
        "--rate_limiter",
        dest="rate_limiter",
        action="store_true",
        help="use RATE LIMITER in learning stage or not",
        default=False,
    )

    (options, args) = parser.parse_args()

    if options.project is None:
        parser.error("parameter project required")

    if options.test is None:
        parser.error("parameter test required")

    if options.stage is None:
        parser.error("parameter stage required")
    elif options.stage not in [sieve_stages.LEARN, sieve_stages.TEST]:
        parser.error("invalid stage option: %s" % options.stage)

    if options.stage == sieve_stages.LEARN:
        if options.mode is None:
            options.mode = sieve_modes.LEARN_ONCE
        elif options.mode not in [
            sieve_modes.LEARN_ONCE,
            sieve_modes.LEARN_TWICE,
        ]:
            parser.error("invalid learn mode option: %s" % options.mode)
        options.config = "learn.yaml"

    if options.stage == sieve_stages.TEST:
        if options.mode is None:
            parser.error("parameter mode required in test stage")
        elif options.mode not in [
            sieve_modes.VANILLA,
            sieve_modes.STALE_STATE,
            sieve_modes.UNOBSR_STATE,
            sieve_modes.INTERMEDIATE_STATE,
        ]:
            parser.error("invalid test mode option: %s" % options.mode)
        if options.mode == sieve_modes.VANILLA:
            options.config = "vanilla.yaml"
        else:
            if options.config is None:
                parser.error("parameter config required in test stage")

    if options.phase not in [
        "all",
        "setup",
        "workload",
        "check",
        "setup_workload",
        "workload_check",
    ]:
        parser.error("invalid phase option: %s" % options.phase)

    print("Running Sieve with %s: %s..." % (options.stage, options.mode))

    if options.batch:
        run_batch(
            options.project,
            options.test,
            options.log,
            options.mode,
            options.stage,
            options.docker,
        )
    else:
        if options.mode == sieve_modes.LEARN_TWICE:
            # Run learn-once first
            run(
                options.project,
                options.test,
                options.log,
                sieve_modes.LEARN_ONCE,
                options.stage,
                options.config,
                options.docker,
                options.rate_limiter,
                options.phase,
            )

        ret_val, report = run(
            options.project,
            options.test,
            options.log,
            options.mode,
            options.stage,
            options.config,
            options.docker,
            options.rate_limiter,
            options.phase,
        )

        save_run_result(
            options.project,
            options.test,
            options.mode,
            options.stage,
            options.config,
            ret_val,
            report,
            start_time,
        )
    print("Total time: {} seconds".format(time.time() - start_time))
