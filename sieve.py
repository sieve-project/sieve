from typing import Tuple
import docker
import optparse
import os
import kubernetes
import sieve_config
import time
import json
import glob
import analyze
import controllers
import oracle
import yaml
import subprocess
import signal
import errno
from datetime import datetime
from common import (
    cprint,
    bcolors,
    fail,
    ok,
    sieve_modes,
    cmd_early_exit,
    NO_ERROR_MESSAGE,
    sieve_stages,
)

def save_run_result(project, test, mode, stage, test_config, alarm, bug_report, starttime):
    if stage is sieve_stages.TEST or mode is sieve_modes.VANILLA:
        return

    result_map = {
        project: {
            test: {
                mode:{
                    test_config: {
                        "duration": time.time() - starttime,
                        "alarm": alarm,
                        "bug_report": bug_report,
                        "test_config_content": open(test_config).read(),
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

    # XXX: Temporarily copy log information to save it for later analysis
    test_log_save = os.path.join("log_save", project, test, stage)
    os.system("mkdir -p {}".format(test_log_save))
    os.system(
        "cp -r {} {}".format(
            log_dir,
            os.path.join(
                test_log_save,
                os.path.splitext(os.path.basename(test_config))[0],
            ),
        )
    )


def watch_crd(project, addrs):
    for addr in addrs:
        for crd in controllers.CRDs[project]:
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


def redirect_workers(num_workers):
    target_master = sieve_config.config["time_travel_front_runner"]
    for i in range(num_workers):
        worker = "kind-worker" + (str(i + 1) if i > 0 else "")
        cmd_early_exit(
            "docker exec %s bash -c \"sed -i 's/kind-external-load-balancer/%s/g' /etc/kubernetes/kubelet.conf\""
            % (worker, target_master)
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


def prepare_sieve_server(test_config):
    cmd_early_exit("cp %s sieve-server/server.yaml" % test_config)
    org_dir = os.getcwd()
    os.chdir("sieve-server")
    cmd_early_exit("go mod tidy")
    cmd_early_exit("go build")
    os.chdir(org_dir)
    cmd_early_exit("docker cp sieve-server kind-control-plane:/sieve-server")


def start_sieve_server():
    cmd_early_exit(
        "docker exec kind-control-plane bash -c 'cd /sieve-server && ./sieve-server &> sieve-server.log &'"
    )


def stop_sieve_server():
    cmd_early_exit("docker exec kind-control-plane bash -c 'pkill sieve-server'")


def setup_kind_cluster(kind_config, docker_repo, docker_tag):
    cmd_early_exit(
        "kind create cluster --image %s/node:%s --config %s"
        % (docker_repo, docker_tag, kind_config)
    )
    cmd_early_exit(
        "docker exec kind-control-plane bash -c 'mkdir -p /root/.kube/ && cp /etc/kubernetes/admin.conf /root/.kube/config'"
    )


def setup_cluster(
    project,
    stage,
    mode,
    test_config,
    docker_repo,
    docker_tag,
    num_apiservers,
    num_workers,
    use_csi_driver,
):
    cmd_early_exit("kind delete cluster")
    setup_kind_cluster(
        generate_kind_config(num_apiservers, num_workers), docker_repo, docker_tag
    )
    print("\n\n")

    # cmd_early_exit("kubectl create namespace %s" % sieve_config["namespace"])
    # cmd_early_exit("kubectl config set-context --current --namespace=%s" %
    #           sieve_config["namespace"])
    prepare_sieve_server(test_config)

    # when testing time-travel, we need to pause the apiserver
    # if workers talks to the paused apiserver, the whole cluster will be slowed down
    # so we need to redirect the workers to other apiservers
    if mode == sieve_modes.TIME_TRAVEL:
        redirect_workers(num_workers)
        redirect_kubectl()

    configmap = generate_configmap(test_config)
    cmd_early_exit("kubectl apply -f %s" % configmap)

    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()

    # Then we wait apiservers to be ready
    print("Waiting for apiservers to be ready...")
    apiserver_list = []
    for i in range(num_apiservers):
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

    for apiserver in apiserver_list:
        cmd_early_exit(
            "kubectl cp %s %s:/sieve.yaml -n kube-system" % (test_config, apiserver)
        )

    # Preload operator image to kind nodes
    image = "%s/%s:%s" % (docker_repo, project, docker_tag)
    kind_load_cmd = "kind load docker-image %s" % (image)
    print("Loading image %s to kind nodes..." % (image))
    if cmd_early_exit(kind_load_cmd, early_exit=False) != 0:
        print("Cannot load image %s locally, try to pull from remote" % (image))
        cmd_early_exit("docker pull %s" % (image))
        cmd_early_exit(kind_load_cmd)

    # csi driver can only work with one apiserver so it cannot be enabled in time travel mode
    if mode != sieve_modes.TIME_TRAVEL and use_csi_driver:
        print("Installing csi provisioner...")
        cmd_early_exit("cd csi-driver && ./install.sh")


def start_operator(project, docker_repo, docker_tag, num_apiservers):
    controllers.deploy[project](docker_repo, docker_tag)

    kubernetes.config.load_kube_config()
    core_v1 = kubernetes.client.CoreV1Api()

    # Wait for project pod ready
    print("Wait for operator pod ready...")
    for tick in range(600):
        project_pod = core_v1.list_namespaced_pod(
            sieve_config.config["namespace"],
            watch=False,
            label_selector="sievetag=" + project,
        ).items
        if len(project_pod) >= 1:
            if project_pod[0].status.phase == "Running":
                break
        time.sleep(1)

    apiserver_addr_list = []
    for i in range(num_apiservers):
        label_selector = "kubernetes.io/hostname=kind-control-plane" + (
            "" if i == 0 else str(i + 1)
        )
        apiserver_addr = (
            "https://"
            + core_v1.list_node(watch=False, label_selector=label_selector)
            .items[0]
            .status.addresses[0]
            .address
            + ":6443"
        )
        apiserver_addr_list.append(apiserver_addr)
    watch_crd(project, apiserver_addr_list)


def run_workload(
    project,
    mode,
    test_workload,
    test_config,
    log_dir,
    docker_repo,
    docker_tag,
    num_apiservers,
) -> Tuple[int, str]:
    if mode != sieve_modes.VANILLA:
        cprint("Setting up Sieve server...", bcolors.OKGREEN)
        start_sieve_server()
        ok("Sieve server set up")

    cprint("Deploying operator...", bcolors.OKGREEN)
    start_operator(project, docker_repo, docker_tag, num_apiservers)
    ok("Operator deployed")

    kubernetes.config.load_kube_config()
    pod_name = (
        kubernetes.client.CoreV1Api()
        .list_namespaced_pod(
            sieve_config.config["namespace"],
            watch=False,
            label_selector="sievetag=" + project,
        )
        .items[0]
        .metadata.name
    )
    streamed_log_file = open(os.path.join(log_dir, "streamed-operator.log"), "w+")
    streaming = subprocess.Popen(
        "kubectl logs %s -f" % pod_name,
        stdout=streamed_log_file,
        stderr=streamed_log_file,
        shell=True,
        preexec_fn=os.setsid,
    )

    cprint("Running test workload...", bcolors.OKGREEN)
    test_workload.run(mode, os.path.join(log_dir, "workload.log"))

    pod_name = (
        kubernetes.client.CoreV1Api()
        .list_namespaced_pod(
            sieve_config.config["namespace"],
            watch=False,
            label_selector="sievetag=" + project,
        )
        .items[0]
        .metadata.name
    )

    for i in range(num_apiservers):
        apiserver_name = "kube-apiserver-kind-control-plane" + (
            "" if i == 0 else str(i + 1)
        )
        apiserver_log = "apiserver%s.log" % (str(i + 1))
        cmd_early_exit(
            "kubectl logs %s -n kube-system > %s/%s"
            % (apiserver_name, log_dir, apiserver_log)
        )

    if mode != sieve_modes.VANILLA:
        cmd_early_exit(
            "docker cp kind-control-plane:/sieve-server/sieve-server.log %s/sieve-server.log"
            % (log_dir)
        )

    cmd_early_exit("kubectl logs %s > %s/operator.log" % (pod_name, log_dir))
    os.killpg(streaming.pid, signal.SIGTERM)
    streamed_log_file.close()
    if mode != sieve_modes.VANILLA:
        stop_sieve_server()


def check_result(
    project, mode, stage, test_config, log_dir, data_dir, oracle_config
) -> Tuple[int, str]:
    if stage == sieve_stages.LEARN:
        analyze.analyze_trace(
            project,
            log_dir,
            canonicalize_resource=(mode == sieve_modes.LEARN_TWICE),
        )
        cmd_early_exit("mkdir -p %s" % data_dir)
        if mode == sieve_modes.LEARN_ONCE:
            cmd_early_exit(
                "cp %s %s"
                % (
                    os.path.join(log_dir, "status.json"),
                    os.path.join(data_dir, "status.json"),
                )
            )
            cmd_early_exit(
                "cp %s %s"
                % (
                    os.path.join(log_dir, "side-effect.json"),
                    os.path.join(data_dir, "side-effect.json"),
                )
            )
        if mode == sieve_modes.LEARN_TWICE:
            cmd_early_exit(
                "cp %s %s"
                % (
                    os.path.join(log_dir, "resources.json"),
                    os.path.join(data_dir, "resources.json"),
                )
            )
    else:
        if mode != sieve_modes.VANILLA:
            if os.path.exists(test_config):
                open(os.path.join(log_dir, "config.yaml"), "w").write(
                    open(test_config).read()
                )
            learned_side_effect = json.load(
                open(os.path.join(data_dir, "side-effect.json"))
            )
            learned_status = json.load(open(os.path.join(data_dir, "status.json")))
            resources_path = os.path.join(data_dir, "resources.json")
            learned_resources = (
                json.load(open(resources_path))
                if os.path.isfile(resources_path)
                else None
            )
            (
                testing_side_effect,
                testing_status,
                testing_resources,
            ) = oracle.generate_digest(log_dir)
            operator_log = os.path.join(log_dir, "streamed-operator.log")
            server_log = os.path.join(log_dir, "sieve-server.log")
            workload_log = os.path.join(log_dir, "workload.log")
            alarm, bug_report = oracle.check(
                learned_side_effect,
                learned_status,
                learned_resources,
                testing_side_effect,
                testing_status,
                testing_resources,
                test_config,
                operator_log,
                server_log,
                oracle_config,
                workload_log,
            )
            open(os.path.join(log_dir, "bug-report.txt"), "w").write(bug_report)
            json.dump(
                testing_side_effect,
                open(os.path.join(log_dir, "side-effect.json"), "w"),
                indent=4,
            )
            json.dump(
                testing_status,
                open(os.path.join(log_dir, "status.json"), "w"),
                indent=4,
            )
            json.dump(
                testing_resources,
                open(os.path.join(log_dir, "resources.json"), "w"),
                indent=4,
            )
            return alarm, bug_report
    return 0, NO_ERROR_MESSAGE


def run_test(
    project,
    mode,
    stage,
    test_workload,
    test_config,
    log_dir,
    docker_repo,
    docker_tag,
    num_apiservers,
    num_workers,
    use_csi_driver,
    oracle_config,
    data_dir,
    phase,
) -> Tuple[int, str]:
    if phase == "all" or phase == "setup_only":
        setup_cluster(
            project,
            stage,
            mode,
            test_config,
            docker_repo,
            docker_tag,
            num_apiservers,
            num_workers,
            use_csi_driver,
        )
    if phase == "all" or phase == "workload_only" or phase == "workload_and_check":
        run_workload(
            project,
            mode,
            test_workload,
            test_config,
            log_dir,
            docker_repo,
            docker_tag,
            num_apiservers,
        )
    if phase == "all" or phase == "check_only" or phase == "workload_and_check":
        alarm, bug_report = check_result(
            project,
            mode,
            stage,
            test_config,
            log_dir,
            data_dir,
            oracle_config,
        )
        if alarm != 0:
            oracle.print_error_and_debugging_info(alarm, bug_report, test_config)
        return alarm, bug_report
    return 0, NO_ERROR_MESSAGE


def generate_learn_config(learn_config, project, mode, rate_limiter_enabled):
    learn_config_map = {}
    learn_config_map["stage"] = sieve_stages.LEARN
    learn_config_map["mode"] = mode
    learn_config_map["crd-list"] = controllers.CRDs[project]
    if rate_limiter_enabled:
        learn_config_map["rate-limiter-enabled"] = "true"
        print("Turn on rate limiter")
    else:
        learn_config_map["rate-limiter-enabled"] = "false"
        print("Turn off rate limiter")
    # hardcode the interval to 3 seconds for now
    learn_config_map["rate-limiter-interval"] = "3"
    yaml.dump(learn_config_map, open(learn_config, "w"), sort_keys=False)


def run(
    test_suites,
    project,
    test,
    log_dir,
    mode,
    stage,
    config,
    docker,
    rate_limiter_enabled=False,
    phase="all",
):
    suite = test_suites[project][test]
    data_dir = os.path.join("data", project, test, sieve_stages.LEARN)
    print("Log dir: %s" % log_dir)
    if phase == "all" or phase == "setup_only":
        cmd_early_exit("rm -rf %s" % log_dir)
        cmd_early_exit("mkdir -p %s" % log_dir)

    if stage == sieve_stages.LEARN:
        learn_config = os.path.join(log_dir, "learn.yaml")
        print("Learning stage with config %s" % learn_config)
        generate_learn_config(
            learn_config, project, sieve_stages.LEARN, rate_limiter_enabled
        )
        return run_test(
            project,
            mode,
            stage,
            suite.workload,
            learn_config,
            log_dir,
            docker,
            stage,
            suite.num_apiservers,
            suite.num_workers,
            suite.use_csi_driver,
            suite.oracle_config,
            data_dir,
            phase,
        )
    else:
        if mode == sieve_modes.VANILLA:
            blank_config = "config/none.yaml"
            return run_test(
                project,
                mode,
                stage,
                suite.workload,
                blank_config,
                log_dir,
                docker,
                mode,
                suite.num_apiservers,
                suite.num_workers,
                suite.use_csi_driver,
                suite.oracle_config,
                data_dir,
                phase,
            )
        else:
            test_config = config
            print("Testing with config: %s" % test_config)
            test_config_to_use = os.path.join(log_dir, os.path.basename(test_config))
            cmd_early_exit("cp %s %s" % (test_config, test_config_to_use))
            if mode == sieve_modes.TIME_TRAVEL and suite.num_apiservers < 3:
                suite.num_apiservers = 3
            elif suite.use_csi_driver:
                suite.num_apiservers = 1
                suite.num_workers = 0

            return run_test(
                project,
                mode,
                stage,
                suite.workload,
                test_config_to_use,
                log_dir,
                docker,
                mode,
                suite.num_apiservers,
                suite.num_workers,
                suite.use_csi_driver,
                suite.oracle_config,
                data_dir,
                phase,
            )


def run_batch(project, test, dir, mode, stage, docker):
    assert stage == sieve_stages.TEST, "can only run batch mode in test stage"
    config_dir = os.path.join(
        "log", project, test, sieve_stages.LEARN, sieve_modes.LEARN_ONCE, mode
    )
    configs = glob.glob(os.path.join(config_dir, "*.yaml"))
    configs.sort(key=lambda config: config.split("-")[-1].split(".")[0])
    print("Configs to test:")
    print("\n".join(configs))
    batch_test_result_tsv = open(
        "sieve_%s_%s_%s.tsv" % (project, test, mode),
        "w",
    )
    result_map = {}
    for config in configs:
        s = time.time()
        num = os.path.basename(config).split(".")[0]
        log_dir = os.path.join(dir, project, test, stage, mode + "-batch", num)
        try:
            if mode == sieve_modes.LEARN_TWICE:
                # Run learn-once first
                run(
                    controllers.test_suites,
                    project,
                    test,
                    os.path.join(
                        dir,
                        project,
                        test,
                        stage,
                        sieve_modes.LEARN_ONCE + "-batch",
                        num,
                    ),
                    sieve_modes.LEARN_ONCE,
                    stage,
                    config,
                    docker,
                )

            alarm, bug_report = run(
                controllers.test_suites,
                project,
                test,
                log_dir,
                mode,
                stage,
                config,
                docker,
            )
            duration = time.time() - s
            if alarm != 0:
                cprint("Bug happens when running %s" % config, bcolors.FAIL)
            result_map[config] = {
                "duration": duration,
                "alarm": alarm,
                "bug_report": bug_report,
            }
            batch_test_result_tsv.write(
                "%s\t%f\t%d\t%s\n"
                % (config, duration, alarm, bug_report.replace("\n", "[EOL]"))
            )
            batch_test_result_tsv.flush()
        except Exception as err:
            duration = time.time() - s
            print("Error occurs when running %s: %s" % (config, repr(err)))
            result_map[config] = {
                "duration": duration,
                "alarm": -1,
                "bug_report": repr(err),
            }
            batch_test_result_tsv.write(
                "%s\t%f\t%d\t%s\n"
                % (config, duration, -1, repr(err).replace("\n", "[EOL]"))
            )
            batch_test_result_tsv.flush()
    batch_test_result_tsv.close()
    batch_test_result_json = open(
        "sieve_%s_%s_%s.json" % (project, test, mode),
        "w",
    )
    json.dump(
        result_map,
        batch_test_result_json,
        indent=4,
    )
    batch_test_result_json.close()


if __name__ == "__main__":
    s = time.time()
    usage = "usage: python3 sieve.py [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option(
        "-p",
        "--project",
        dest="project",
        help="specify PROJECT to test",
        metavar="PROJECT",
        # default="cassandra-operator",
    )
    parser.add_option(
        "-t",
        "--test",
        dest="test",
        help="specify TEST to run",
        metavar="TEST",
        # default="recreate",
    )
    parser.add_option(
        "-d",
        "--docker",
        dest="docker",
        help="DOCKER repo that you have access",
        metavar="DOCKER",
        default=sieve_config.config["docker_repo"],
    )
    parser.add_option(
        "-l", "--log", dest="log", help="save to LOG", metavar="LOG", default="log"
    )
    parser.add_option(
        "-m",
        "--mode",
        dest="mode",
        help="test MODE: vanilla, time-travel, obs-gap, atom-vio",
        metavar="MODE",
        # default=sieve_modes.NONE,
    )
    parser.add_option(
        "-c",
        "--config",
        dest="config",
        help="test CONFIG",
        metavar="CONFIG",
        # default="none",
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
        help="run the PHASE: setup_only, workload_only, check_only or all",
        metavar="PHASE",
        default="all",
    )
    parser.add_option(
        "-s",
        "--stage",
        dest="stage",
        help="STAGE: learn, test",
        # default=sieve_stages.TEST,
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

    if options.stage is None:
        parser.error("parameter stage required")

    if options.test is None:
        parser.error("parameter test required")

    if options.stage not in [sieve_stages.LEARN, sieve_stages.TEST]:
        parser.error("invalid stage option: %s" % options.stage)

    if options.stage == sieve_stages.LEARN and options.mode is None:
        options.mode = sieve_modes.LEARN_ONCE

    if options.stage == sieve_stages.TEST and options.mode is None:
        parser.error("parameter mode required in test stage")

    if options.stage == sieve_stages.TEST and options.config is None:
        parser.error("parameter config required in test stage")

    if options.mode == "obs-gap":
        options.mode = sieve_modes.OBS_GAP
    elif options.mode == "atom-vio":
        options.mode = sieve_modes.ATOM_VIO

    if options.stage == sieve_stages.LEARN and options.mode not in [
        sieve_modes.LEARN_ONCE,
        sieve_modes.LEARN_TWICE,
    ]:
        parser.error("invalid learn mode option: %s" % options.mode)

    if options.stage == sieve_stages.TEST and options.mode not in [
        sieve_modes.VANILLA,
        sieve_modes.TIME_TRAVEL,
        sieve_modes.OBS_GAP,
        sieve_modes.ATOM_VIO,
    ]:
        parser.error("invalid test mode option: %s" % options.mode)

    if options.phase not in [
        "all",
        "setup_only",
        "workload_only",
        "check_only",
        "workload_and_check",
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
        log_dir = os.path.join(
            options.log, options.project, options.test, options.stage, options.mode
        )

        if options.mode == sieve_modes.LEARN_TWICE:
            # Run learn-once first
            run(
                controllers.test_suites,
                options.project,
                options.test,
                os.path.join(
                    options.log,
                    options.project,
                    options.test,
                    options.stage,
                    sieve_modes.LEARN_ONCE,
                ),
                sieve_modes.LEARN_ONCE,
                options.stage,
                options.config,
                options.docker,
                options.rate_limiter,
                options.phase,
            )

        alarm, report = run(
            controllers.test_suites,
            options.project,
            options.test,
            log_dir,
            options.mode,
            options.stage,
            options.config,
            options.docker,
            options.rate_limiter,
            options.phase,
        )

        save_run_result(options.project, options.test, options.mode, options.stage, options.config, alarm, report, s)
    print("Total time: {} seconds".format(time.time() - s))
