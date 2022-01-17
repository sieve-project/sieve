from sieve_common.common import sieve_modes, cmd_early_exit, sieve_stages
import os
import controllers
import optparse
import fileinput
from sieve_common.default_config import sieve_config

ORIGINAL_DIR = os.getcwd()

DEFAULT_K8S_VERSION = "v1.18.9"
K8S_VER_TO_LIB_VER = {"v1.18.9": "v0.18.9", "v1.23.1": "v0.23.1"}


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
            K8S_VER_TO_LIB_VER[version],
        )
    cmd_early_exit(
        "ln -s ../staging/src/sieve.client fakegopath/src/k8s.io/kubernetes/vendor/sieve.client"
    )


def instrument_kubernetes(mode):
    os.chdir("sieve_instrumentation")
    cmd_early_exit("go build")
    cmd_early_exit(
        "./instrumentation kubernetes %s %s/fakegopath/src/k8s.io/kubernetes"
        % (mode, ORIGINAL_DIR)
    )
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
    cmd_early_exit("docker push %s/node:%s" % (img_repo, img_tag))
    os.chdir(ORIGINAL_DIR)


def setup_kubernetes(version, mode, img_repo, img_tag):
    download_kubernetes(version)
    install_lib_for_kubernetes(version)
    instrument_kubernetes(mode)
    build_kubernetes(version, img_repo, img_tag)


def download_controller(project, link, sha):
    # If for some permission issue that we can't remove the operator, try sudo
    if (
        cmd_early_exit("rm -rf %s" % controllers.app_dir[project], early_exit=False)
        != 0
    ):
        print("We cannot remove %s, try sudo instead" % controllers.app_dir[project])
        cmd_early_exit("sudo rm -rf %s" % controllers.app_dir[project])
    cmd_early_exit(
        "git clone %s %s >> /dev/null" % (link, controllers.app_dir[project])
    )
    os.chdir(controllers.app_dir[project])
    cmd_early_exit("git checkout %s >> /dev/null" % sha)
    cmd_early_exit("git checkout -b sieve >> /dev/null")
    if project == "cassandra-operator":
        cmd_early_exit("git cherry-pick bd8077a478997f63862848d66d4912c59e4c46ff")
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
    project, controller_runtime_version, client_go_version, docker_file_path
):
    # download controller_runtime and client_go libs
    cmd_early_exit(
        "go mod download sigs.k8s.io/controller-runtime@%s >> /dev/null"
        % controller_runtime_version
    )
    cmd_early_exit(
        "mkdir -p %s/dep-sieve/src/sigs.k8s.io" % controllers.app_dir[project]
    )
    cmd_early_exit(
        "cp -r ${GOPATH}/pkg/mod/sigs.k8s.io/controller-runtime@%s %s/dep-sieve/src/sigs.k8s.io/controller-runtime@%s"
        % (
            controller_runtime_version,
            controllers.app_dir[project],
            controller_runtime_version,
        )
    )
    cmd_early_exit(
        "chmod +w -R %s/dep-sieve/src/sigs.k8s.io/controller-runtime@%s"
        % (controllers.app_dir[project], controller_runtime_version)
    )
    cmd_early_exit(
        "go mod download k8s.io/client-go@%s >> /dev/null" % client_go_version
    )
    cmd_early_exit("mkdir -p %s/dep-sieve/src/k8s.io" % controllers.app_dir[project])
    cmd_early_exit(
        "cp -r ${GOPATH}/pkg/mod/k8s.io/client-go@%s %s/dep-sieve/src/k8s.io/client-go@%s"
        % (client_go_version, controllers.app_dir[project], client_go_version)
    )
    cmd_early_exit(
        "chmod +w -R %s/dep-sieve/src/k8s.io/client-go@%s"
        % (controllers.app_dir[project], client_go_version)
    )
    cmd_early_exit(
        "cp -r sieve_client %s/dep-sieve/src/sieve.client"
        % controllers.app_dir[project]
    )
    if controllers.kubernetes_version[project] != DEFAULT_K8S_VERSION:
        update_sieve_client_go_mod_with_version(
            "%s/dep-sieve/src/sieve.client/go.mod" % controllers.app_dir[project],
            K8S_VER_TO_LIB_VER[controllers.kubernetes_version[project]],
        )

    if project == "yugabyte-operator":
        # Ad-hoc fix for api incompatibility in golang
        # Special handling of yugabyte-operator as it depends on an older apimachinery which is
        # incompatible with the one sieve.client depends on
        with fileinput.FileInput(
            "%s/dep-sieve/src/sieve.client/go.mod" % controllers.app_dir[project],
            inplace=True,
            backup=".bak",
        ) as sieve_client_go_mod:
            for line in sieve_client_go_mod:
                if "k8s.io/apimachinery" in line:
                    print("\tk8s.io/apimachinery v0.17.4", end="\n")
                else:
                    print(line, end="")

    os.chdir(controllers.app_dir[project])
    cmd_early_exit("git add -A >> /dev/null")
    cmd_early_exit('git commit -m "download the lib" >> /dev/null')
    os.chdir(ORIGINAL_DIR)

    # modify the go.mod to import the libs
    remove_replacement_in_go_mod_file("%s/go.mod" % controllers.app_dir[project])
    with open("%s/go.mod" % controllers.app_dir[project], "a") as go_mod_file:
        go_mod_file.write("require sieve.client v0.0.0\n")
        go_mod_file.write("replace sieve.client => ./dep-sieve/src/sieve.client\n")
        go_mod_file.write(
            "replace sigs.k8s.io/controller-runtime => ./dep-sieve/src/sigs.k8s.io/controller-runtime@%s\n"
            % controller_runtime_version
        )
        go_mod_file.write(
            "replace k8s.io/client-go => ./dep-sieve/src/k8s.io/client-go@%s\n"
            % client_go_version
        )
    with open(
        "%s/dep-sieve/src/sigs.k8s.io/controller-runtime@%s/go.mod"
        % (controllers.app_dir[project], controller_runtime_version),
        "a",
    ) as go_mod_file:
        go_mod_file.write("require sieve.client v0.0.0\n")
        go_mod_file.write("replace sieve.client => ../../sieve.client\n")
        go_mod_file.write(
            "replace k8s.io/client-go => ../../k8s.io/client-go@%s\n"
            % client_go_version
        )
    with open(
        "%s/dep-sieve/src/k8s.io/client-go@%s/go.mod"
        % (controllers.app_dir[project], client_go_version),
        "a",
    ) as go_mod_file:
        go_mod_file.write("require sieve.client v0.0.0\n")
        go_mod_file.write("replace sieve.client => ../../sieve.client\n")

    # copy the build.sh and Dockerfile
    cmd_early_exit(
        "cp %s/build/build.sh %s/build.sh"
        % (controllers.test_dir[project], controllers.app_dir[project])
    )
    cmd_early_exit(
        "cp %s/build/Dockerfile %s/%s"
        % (
            controllers.test_dir[project],
            controllers.app_dir[project],
            docker_file_path,
        )
    )
    os.chdir(controllers.app_dir[project])
    cmd_early_exit("git add -A >> /dev/null")
    cmd_early_exit('git commit -m "import the lib" >> /dev/null')
    os.chdir(ORIGINAL_DIR)


def instrument_controller(project, mode, controller_runtime_version, client_go_version):
    os.chdir("sieve_instrumentation")
    cmd_early_exit("go build")
    cmd_early_exit(
        "./instrumentation %s %s %s/%s/dep-sieve/src/sigs.k8s.io/controller-runtime@%s %s/%s/dep-sieve/src/k8s.io/client-go@%s"
        % (
            project,
            mode,
            ORIGINAL_DIR,
            controllers.app_dir[project],
            controller_runtime_version,
            ORIGINAL_DIR,
            controllers.app_dir[project],
            client_go_version,
        )
    )
    os.chdir(ORIGINAL_DIR)


def build_controller(project, img_repo, img_tag):
    os.chdir(controllers.app_dir[project])
    cmd_early_exit("./build.sh %s %s" % (img_repo, img_tag))
    os.chdir(ORIGINAL_DIR)


def setup_controller(
    project,
    mode,
    img_repo,
    img_tag,
    link,
    sha,
    controller_runtime_version,
    client_go_version,
    docker_file_path,
    build_only,
):
    if not build_only:
        download_controller(project, link, sha)
        install_lib_for_controller(
            project, controller_runtime_version, client_go_version, docker_file_path
        )
        instrument_controller(
            project, mode, controller_runtime_version, client_go_version
        )
    build_controller(project, img_repo, img_tag)


def setup_kubernetes_wrapper(version, mode, img_repo):
    img_tag = version + "-" + mode
    if mode == "all":
        for this_mode in [
            sieve_stages.LEARN,
            sieve_modes.ATOM_VIO,
            sieve_modes.OBS_GAP,
            sieve_modes.TIME_TRAVEL,
        ]:
            setup_kubernetes(version, this_mode, img_repo, img_tag)
    else:
        setup_kubernetes(version, mode, img_repo, img_tag)


def setup_controller_wrapper(controller, mode, img_repo, sha, build_only):
    img_tag = mode
    if mode == "all":
        for this_mode in [
            sieve_stages.LEARN,
            sieve_modes.ATOM_VIO,
            sieve_modes.OBS_GAP,
            sieve_modes.TIME_TRAVEL,
        ]:
            img_tag = this_mode
            setup_controller(
                controller,
                this_mode,
                img_repo,
                img_tag,
                controllers.github_link[controller],
                sha,
                controllers.controller_runtime_version[controller],
                controllers.client_go_version[controller],
                controllers.docker_file[controller],
                build_only,
            )
    else:
        setup_controller(
            controller,
            mode,
            img_repo,
            img_tag,
            controllers.github_link[controller],
            sha,
            controllers.controller_runtime_version[controller],
            controllers.client_go_version[controller],
            controllers.docker_file[controller],
            build_only,
        )


if __name__ == "__main__":
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
        help="build MODE: learn, time-travel, obs-gap, atom-vio",
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
        default=None,
    )
    parser.add_option(
        "-b",
        "--build",
        dest="build_only",
        action="store_true",
        help="build only",
        default=False,
    )
    (options, args) = parser.parse_args()

    if options.project is None:
        parser.error("parameter project required")

    if options.mode is None:
        parser.error("parameter mode required")

    if options.mode == "obs-gap":
        options.mode = sieve_modes.OBS_GAP
    elif options.mode == "atom-vio":
        options.mode = sieve_modes.ATOM_VIO
    if options.project == "k8s":
        options.project = "kubernetes"

    if options.mode not in [
        sieve_modes.VANILLA,
        sieve_modes.TIME_TRAVEL,
        sieve_modes.OBS_GAP,
        sieve_modes.ATOM_VIO,
        sieve_stages.LEARN,
        sieve_modes.ALL,
    ]:
        parser.error("invalid build mode option: %s" % options.mode)

    img_repo = (
        options.docker if options.docker is not None else sieve_config["docker_repo"]
    )
    if options.project == "kubernetes":
        setup_kubernetes_wrapper(options.version, options.mode, img_repo)
    elif options.project == "all":
        for controller in controllers.github_link:
            setup_controller_wrapper(
                controller,
                options.mode,
                img_repo,
                controllers.sha[controller],
                options.build_only,
            )
    else:
        sha = (
            options.sha if options.sha is not None else controllers.sha[options.project]
        )
        setup_controller_wrapper(
            options.project,
            options.mode,
            img_repo,
            sha,
            options.build_only,
        )
