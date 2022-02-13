from sieve_common.common import (
    sieve_modes,
    cmd_early_exit,
    sieve_stages,
    get_all_controllers,
)
import os
import optparse
import json
from sieve_common.default_config import (
    CommonConfig,
    get_controller_config,
    get_common_config,
    ControllerConfig,
)

ORIGINAL_DIR = os.getcwd()

DEFAULT_K8S_VERSION = "v1.18.9"
K8S_VER_TO_APIMACHINERY_VER = {"v1.18.9": "v0.18.9", "v1.23.1": "v0.23.1"}


def update_sieve_client_go_mod_with_version(go_mod_path, version):
    fin = open(go_mod_path)
    data = fin.read()
    data = data.replace(
        "k8s.io/apimachinery v0.18.9",
        "k8s.io/apimachinery %s" % version,
    )
    fin.close()
    fout = open(go_mod_path, "w")
    fout.write(data)
    fout.close()


def download_kubernetes(version):
    cmd_early_exit("rm -rf fakegopath")
    cmd_early_exit("mkdir -p fakegopath/src/k8s.io")
    cmd_early_exit(
        "git clone --single-branch --branch %s https://github.com/kubernetes/kubernetes.git fakegopath/src/k8s.io/kubernetes >> /dev/null"
        % version
    )
    os.chdir("fakegopath/src/k8s.io/kubernetes")
    cmd_early_exit("git checkout -b sieve >> /dev/null")
    os.chdir(ORIGINAL_DIR)


def install_lib_for_kubernetes(version):
    with open(
        "fakegopath/src/k8s.io/kubernetes/staging/src/k8s.io/apiserver/go.mod", "a"
    ) as go_mod_file:
        go_mod_file.write("require sieve.client v0.0.0\n")
        go_mod_file.write("replace sieve.client => ../../sieve.client\n")
    cmd_early_exit(
        "cp -r sieve_client fakegopath/src/k8s.io/kubernetes/staging/src/sieve.client"
    )
    if version != DEFAULT_K8S_VERSION:
        update_sieve_client_go_mod_with_version(
            "fakegopath/src/k8s.io/kubernetes/staging/src/sieve.client/go.mod",
            K8S_VER_TO_APIMACHINERY_VER[version],
        )
    cmd_early_exit(
        "ln -s ../staging/src/sieve.client fakegopath/src/k8s.io/kubernetes/vendor/sieve.client"
    )


def instrument_kubernetes(mode):
    os.chdir("sieve_instrumentation")
    cmd_early_exit("go build")
    instrumentation_config = {
        "project": "kubernetes",
        "mode": mode,
        "k8s_filepath": "%s/fakegopath/src/k8s.io/kubernetes" % (ORIGINAL_DIR),
    }
    json.dump(instrumentation_config, open("config.json", "w"))
    cmd_early_exit("./instrumentation config.json")
    os.chdir(ORIGINAL_DIR)


def build_kubernetes(version, img_repo, img_tag):
    os.chdir("fakegopath/src/k8s.io/kubernetes")
    cmd_early_exit(
        "GOPATH=%s/fakegopath KUBE_GIT_VERSION=%s-sieve-`git rev-parse HEAD` kind build node-image"
        % (ORIGINAL_DIR, version)
    )
    os.chdir(ORIGINAL_DIR)
    os.chdir("build_k8s")
    cmd_early_exit("docker build --no-cache -t %s/node:%s ." % (img_repo, img_tag))
    os.chdir(ORIGINAL_DIR)


def push_kubernetes(img_repo, img_tag):
    cmd_early_exit("docker push %s/node:%s" % (img_repo, img_tag))


def setup_kubernetes(version, mode, img_repo, img_tag, push_to_remote):
    download_kubernetes(version)
    install_lib_for_kubernetes(version)
    instrument_kubernetes(mode)
    build_kubernetes(version, img_repo, img_tag)
    if push_to_remote:
        push_kubernetes(img_repo, img_tag)


def download_controller(
    common_config: CommonConfig,
    controller_config: ControllerConfig,
):
    application_dir = os.path.join("app", controller_config.controller_name)
    # If for some permission issue that we can't remove the operator, try sudo
    if cmd_early_exit("rm -rf %s" % application_dir, early_exit=False) != 0:
        print("We cannot remove %s, try sudo instead" % application_dir)
        cmd_early_exit("sudo rm -rf %s" % application_dir)
    cmd_early_exit(
        "git clone %s %s >> /dev/null"
        % (controller_config.github_link, application_dir)
    )
    os.chdir(application_dir)
    cmd_early_exit("git checkout %s >> /dev/null" % controller_config.commit)
    cmd_early_exit("git checkout -b sieve >> /dev/null")
    for commit in controller_config.cherry_pick_commits:
        cmd_early_exit("git cherry-pick %s" % commit)
    os.chdir(ORIGINAL_DIR)


def remove_replacement_in_go_mod_file(file):
    lines = []
    with open(file, "r") as go_mod_file:
        lines = go_mod_file.readlines()
    with open(file, "w") as go_mod_file:
        for line in lines:
            if "k8s.io/client-go =>" in line:
                continue
            elif "sigs.k8s.io/controller-runtime =>" in line:
                continue
            go_mod_file.write(line)


def install_lib_for_controller(
    common_config: CommonConfig, controller_config: ControllerConfig
):
    application_dir = os.path.join("app", controller_config.controller_name)
    # download controller_runtime and client_go libs
    cmd_early_exit(
        "go mod download sigs.k8s.io/controller-runtime@%s >> /dev/null"
        % controller_config.controller_runtime_version
    )
    cmd_early_exit("mkdir -p %s/sieve-dependency/src/sigs.k8s.io" % application_dir)
    cmd_early_exit(
        "cp -r ${GOPATH}/pkg/mod/sigs.k8s.io/controller-runtime@%s %s/sieve-dependency/src/sigs.k8s.io/controller-runtime@%s"
        % (
            controller_config.controller_runtime_version,
            application_dir,
            controller_config.controller_runtime_version,
        )
    )
    cmd_early_exit(
        "chmod -R +w %s/sieve-dependency/src/sigs.k8s.io/controller-runtime@%s"
        % (
            application_dir,
            controller_config.controller_runtime_version,
        )
    )
    cmd_early_exit(
        "go mod download k8s.io/client-go@%s >> /dev/null"
        % controller_config.client_go_version
    )
    cmd_early_exit("mkdir -p %s/sieve-dependency/src/k8s.io" % application_dir)
    cmd_early_exit(
        "cp -r ${GOPATH}/pkg/mod/k8s.io/client-go@%s %s/sieve-dependency/src/k8s.io/client-go@%s"
        % (
            controller_config.client_go_version,
            application_dir,
            controller_config.client_go_version,
        )
    )
    cmd_early_exit(
        "chmod -R +w %s/sieve-dependency/src/k8s.io/client-go@%s"
        % (application_dir, controller_config.client_go_version)
    )
    cmd_early_exit(
        "cp -r sieve_client %s/sieve-dependency/src/sieve.client" % application_dir
    )
    if controller_config.kubernetes_version != DEFAULT_K8S_VERSION:
        update_sieve_client_go_mod_with_version(
            "%s/sieve-dependency/src/sieve.client/go.mod" % application_dir,
            K8S_VER_TO_APIMACHINERY_VER[controller_config.kubernetes_version],
        )
    elif controller_config.apimachinery_version is not None:
        update_sieve_client_go_mod_with_version(
            "%s/sieve-dependency/src/sieve.client/go.mod" % application_dir,
            controller_config.apimachinery_version,
        )

    os.chdir(application_dir)
    cmd_early_exit("git add -A >> /dev/null")
    cmd_early_exit('git commit -m "download the lib" >> /dev/null')
    os.chdir(ORIGINAL_DIR)

    # modify the go.mod to import the libs
    remove_replacement_in_go_mod_file("%s/go.mod" % application_dir)
    with open("%s/go.mod" % application_dir, "a") as go_mod_file:
        go_mod_file.write("require sieve.client v0.0.0\n")
        go_mod_file.write(
            "replace sieve.client => ./sieve-dependency/src/sieve.client\n"
        )
        go_mod_file.write(
            "replace sigs.k8s.io/controller-runtime => ./sieve-dependency/src/sigs.k8s.io/controller-runtime@%s\n"
            % controller_config.controller_runtime_version
        )
        go_mod_file.write(
            "replace k8s.io/client-go => ./sieve-dependency/src/k8s.io/client-go@%s\n"
            % controller_config.client_go_version
        )
    with open(
        "%s/sieve-dependency/src/sigs.k8s.io/controller-runtime@%s/go.mod"
        % (
            application_dir,
            controller_config.controller_runtime_version,
        ),
        "a",
    ) as go_mod_file:
        go_mod_file.write("require sieve.client v0.0.0\n")
        go_mod_file.write("replace sieve.client => ../../sieve.client\n")
        go_mod_file.write(
            "replace k8s.io/client-go => ../../k8s.io/client-go@%s\n"
            % controller_config.client_go_version
        )
    with open(
        "%s/sieve-dependency/src/k8s.io/client-go@%s/go.mod"
        % (application_dir, controller_config.client_go_version),
        "a",
    ) as go_mod_file:
        go_mod_file.write("require sieve.client v0.0.0\n")
        go_mod_file.write("replace sieve.client => ../../sieve.client\n")

    # copy the build.sh and Dockerfile
    cmd_early_exit(
        "cp %s/build/build.sh %s/build.sh"
        % (
            os.path.join(
                common_config.controller_folder, controller_config.controller_name
            ),
            application_dir,
        )
    )
    cmd_early_exit(
        "cp %s/build/Dockerfile %s/%s"
        % (
            os.path.join(
                common_config.controller_folder, controller_config.controller_name
            ),
            application_dir,
            controller_config.dockerfile_path,
        )
    )
    os.chdir(application_dir)
    cmd_early_exit("git add -A >> /dev/null")
    cmd_early_exit('git commit -m "import the lib" >> /dev/null')
    os.chdir(ORIGINAL_DIR)


def instrument_controller(
    common_config: CommonConfig, controller_config: ControllerConfig, mode
):
    application_dir = os.path.join("app", controller_config.controller_name)
    os.chdir("sieve_instrumentation")
    instrumentation_config = {
        "project": controller_config.controller_name,
        "mode": mode,
        "controller_runtime_filepath": "%s/%s/sieve-dependency/src/sigs.k8s.io/controller-runtime@%s"
        % (
            ORIGINAL_DIR,
            application_dir,
            controller_config.controller_runtime_version,
        ),
        "client_go_filepath": "%s/%s/sieve-dependency/src/k8s.io/client-go@%s"
        % (
            ORIGINAL_DIR,
            application_dir,
            controller_config.client_go_version,
        ),
    }
    json.dump(instrumentation_config, open("config.json", "w"))
    cmd_early_exit("go build")
    cmd_early_exit("./instrumentation config.json")
    os.chdir(ORIGINAL_DIR)


def build_controller(
    common_config: CommonConfig, controller_config: ControllerConfig, img_repo, img_tag
):
    application_dir = os.path.join("app", controller_config.controller_name)
    os.chdir(application_dir)
    cmd_early_exit("./build.sh %s %s" % (img_repo, img_tag))
    os.chdir(ORIGINAL_DIR)
    os.system(
        "docker tag %s %s/%s:%s"
        % (
            controller_config.controller_image_name,
            img_repo,
            controller_config.controller_name,
            img_tag,
        )
    )


def push_controller(
    common_config: CommonConfig, controller_config: ControllerConfig, img_repo, img_tag
):
    cmd_early_exit(
        "docker push %s/%s:%s" % (img_repo, controller_config.controller_name, img_tag)
    )


def setup_controller(
    common_config: CommonConfig,
    controller_config: ControllerConfig,
    mode,
    img_repo,
    img_tag,
    build_only,
    push_to_remote,
):
    if not build_only:
        download_controller(common_config, controller_config)
        install_lib_for_controller(common_config, controller_config)
        instrument_controller(common_config, controller_config, mode)
    build_controller(common_config, controller_config, img_repo, img_tag)
    if push_to_remote:
        push_controller(common_config, controller_config, img_repo, img_tag)


def setup_kubernetes_wrapper(version, mode, img_repo, push_to_remote):
    if mode == "all":
        for this_mode in [
            sieve_stages.LEARN,
            sieve_modes.INTERMEDIATE_STATE,
            sieve_modes.UNOBSR_STATE,
            sieve_modes.STALE_STATE,
        ]:
            img_tag = version + "-" + this_mode
            setup_kubernetes(version, this_mode, img_repo, img_tag, push_to_remote)
    else:
        img_tag = version + "-" + mode
        setup_kubernetes(version, mode, img_repo, img_tag, push_to_remote)


def setup_controller_wrapper(
    common_config: CommonConfig,
    controller_config: ControllerConfig,
    mode,
    img_repo,
    build_only,
    push_to_remote,
):
    img_tag = mode
    if mode == "all":
        for this_mode in [
            sieve_stages.LEARN,
            sieve_modes.INTERMEDIATE_STATE,
            sieve_modes.UNOBSR_STATE,
            sieve_modes.STALE_STATE,
        ]:
            img_tag = this_mode
            setup_controller(
                common_config,
                controller_config,
                this_mode,
                img_repo,
                img_tag,
                build_only,
                push_to_remote,
            )
    else:
        setup_controller(
            common_config,
            controller_config,
            mode,
            img_repo,
            img_tag,
            build_only,
            push_to_remote,
        )


if __name__ == "__main__":
    common_config = get_common_config()
    usage = "usage: python3 build.py [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option(
        "-p",
        "--project",
        dest="project",
        help="specify PROJECT to build: Kubernetes or the controller",
        metavar="PROJECT",
        default=None,
    )
    parser.add_option(
        "-m",
        "--mode",
        dest="mode",
        help="build MODE: learn, stale-state, unobserved-state, intermediate-state",
        metavar="MODE",
        default=None,
    )
    parser.add_option(
        "-v",
        "--version",
        dest="version",
        help="VERSION of Kubernetes",
        metavar="VER",
        default=DEFAULT_K8S_VERSION,
    )
    parser.add_option(
        "-s",
        "--sha",
        dest="sha",
        help="SHA of the controller project",
        metavar="SHA",
        default=None,
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
        "-b",
        "--build",
        dest="build_only",
        action="store_true",
        help="build only",
        default=False,
    )
    parser.add_option("-r", action="store_true", dest="push_to_remote", default=False)
    (options, args) = parser.parse_args()

    if options.project is None:
        parser.error("parameter project required")

    if options.mode is None:
        parser.error("parameter mode required")

    if options.mode not in [
        sieve_modes.VANILLA,
        sieve_modes.STALE_STATE,
        sieve_modes.UNOBSR_STATE,
        sieve_modes.INTERMEDIATE_STATE,
        sieve_stages.LEARN,
        sieve_modes.ALL,
    ]:
        parser.error("invalid build mode option: %s" % options.mode)

    if options.project == "kind":
        setup_kubernetes_wrapper(
            options.version, options.mode, options.docker, options.push_to_remote
        )
    elif options.project == "all":
        all_controllers = get_all_controllers(common_config.controller_folder)
        for controller in all_controllers:
            controller_config = get_controller_config(
                common_config.controller_folder, controller
            )
            setup_controller_wrapper(
                common_config,
                controller_config,
                options.mode,
                options.docker,
                options.build_only,
                options.push_to_remote,
            )
    else:
        controller_config = get_controller_config(
            common_config.controller_folder, options.project
        )
        if options.sha is not None:
            controller_config.commit = options.sha
        setup_controller_wrapper(
            common_config,
            controller_config,
            options.mode,
            options.docker,
            options.build_only,
            options.push_to_remote,
        )
