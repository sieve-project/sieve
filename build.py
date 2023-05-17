from sieve_common.common import (
    sieve_modes,
    os_system,
    add_mod_recursively,
    rmtree_if_exists,
)
import shutil
import os
import stat
import optparse
import json
import sys
from sieve_common.config import (
    CommonConfig,
    load_controller_config,
    get_common_config,
    ControllerConfig,
)

ORIGINAL_DIR = os.getcwd()

GOPATH = os.environ["GOPATH"]

DEFAULT_K8S_VERSION = "v1.18.9"


def k8s_version_to_apimachinery_version(k8s_version):
    """
    Generate the version number of apimachinery imported by sieve client.

    :param k8s_version: the Kubernetes version
    :return: the apimachinery version
    """
    # TODO: It is a bit ad-hoc to decide the compatible apimachinery version
    apimachinery_version = "v0" + k8s_version[2:]
    print(
        "Use the apimachinery version {} in sieve client".format(apimachinery_version)
    )
    return apimachinery_version


def update_sieve_client_go_mod_with_version(go_mod_path, version):
    """
    Update the apimachinery version number in the go.mod of sieve client.
    We need to hack the go.mod because sieve client will be imported by Kubernetes after instrumentation.

    :param go_mod_path: the file path of go.mod in sieve client
    :param version: the apimachinery version number
    """
    fin = open(go_mod_path)
    data = fin.read()
    data = data.replace(
        "k8s.io/apimachinery v0.18.9",
        "k8s.io/apimachinery {}".format(version),
    )
    fin.close()
    fout = open(go_mod_path, "w")
    fout.write(data)
    fout.close()


def download_kubernetes(version):
    """
    Download Kubernetes to fakegopath and checkout to the specified version.

    :param version: the Kubernetes version that will be used to build kind node image
    """
    rmtree_if_exists("fakegopath")
    os.makedirs("fakegopath/src/k8s.io")
    os_system(
        "git clone --single-branch --branch {} https://github.com/kubernetes/kubernetes.git fakegopath/src/k8s.io/kubernetes >> /dev/null".format(
            version
        )
    )
    os.chdir("fakegopath/src/k8s.io/kubernetes")
    os_system("git checkout -b sieve >> /dev/null")
    os.chdir(ORIGINAL_DIR)


def install_lib_for_kubernetes(version):
    """
    Import sieve client to Kubernetes.

    :param version: the Kubernetes version
    """
    with open(
        "fakegopath/src/k8s.io/kubernetes/staging/src/k8s.io/apiserver/go.mod", "a"
    ) as go_mod_file:
        go_mod_file.write("require sieve.client v0.0.0\n")
        go_mod_file.write("replace sieve.client => ../../sieve.client\n")
    shutil.copytree(
        "sieve_client", "fakegopath/src/k8s.io/kubernetes/staging/src/sieve.client"
    )
    if version != DEFAULT_K8S_VERSION:
        update_sieve_client_go_mod_with_version(
            "fakegopath/src/k8s.io/kubernetes/staging/src/sieve.client/go.mod",
            k8s_version_to_apimachinery_version(version),
        )
    os.symlink(
        "../staging/src/sieve.client",
        "fakegopath/src/k8s.io/kubernetes/vendor/sieve.client",
    )


def instrument_kubernetes(mode):
    """
    Instrument the Kubernetes source code using the instrumentation tool.

    :param mode: the building mode which decides the instrumentation
    """
    os.chdir("sieve_instrumentation")
    instrumentation_config = {
        "project": "kubernetes",
        "mode": mode,
        "k8s_filepath": "{}/fakegopath/src/k8s.io/kubernetes".format(ORIGINAL_DIR),
    }
    json.dump(instrumentation_config, open("config.json", "w"), indent=4)
    os_system("go mod tidy")
    os_system("go build")
    os_system("./instrumentation config.json")
    os.chdir(ORIGINAL_DIR)


def build_kubernetes(version, container_registry, image_tag):
    """
    Build the Kubernetes source code into kind node image.

    :param version: the Kubernetes version
    :param container_registry: the name of the container registry as part of the image name
    :param image_tag: the tag of the image
    """
    os.chdir("fakegopath/src/k8s.io/kubernetes")
    os_system(
        "GOPATH={}/fakegopath KUBE_GIT_VERSION={}-sieve-`git rev-parse HEAD` kind build node-image".format(
            ORIGINAL_DIR, version
        )
    )
    os.chdir(ORIGINAL_DIR)
    os_system(
        "docker image tag kindest/node:latest {}/node:{}".format(
            container_registry, image_tag
        )
    )


def push_kubernetes(container_registry, image_tag):
    """
    Push the kind node image to a remote registry.

    :param container_registry: the name of the container registry to push the image to
    :param image_tag: the tag of the image
    """
    os_system("docker push {}/node:{}".format(container_registry, image_tag))


def setup_kubernetes(version, mode, container_registry, image_tag, push_to_remote):
    """
    Download Kubernetes, import sieve client, instrument the source code, build the kind node image
    and push to the remote registry if needed.

    :param version: the Kubernetes version
    :param mode: the building mode which decides what the instrumentation look like
    :param container_registry: the name of the container registry to push the image to
    :param image_tag: the tag of the image
    :param push_to_remote: if true then push the image to container_registry
    """
    download_kubernetes(version)
    install_lib_for_kubernetes(version)
    instrument_kubernetes(mode)
    build_kubernetes(version, container_registry, image_tag)
    if push_to_remote:
        push_kubernetes(container_registry, image_tag)


def download_controller(
    controller_config: ControllerConfig,
):
    """
    Download the controller.

    :param controller_config: the controller configuration
    """
    application_dir = os.path.join("app", controller_config.controller_name)
    rmtree_if_exists(application_dir)
    os_system(
        "git clone {} {} >> /dev/null".format(
            controller_config.github_link, application_dir
        )
    )
    os.chdir(application_dir)
    os_system("git checkout {} >> /dev/null".format(controller_config.commit))
    os_system("git checkout -b sieve >> /dev/null")
    for commit in controller_config.cherry_pick_commits:
        os_system("git cherry-pick {}".format(commit))
    os.chdir(ORIGINAL_DIR)


def install_module(module, sieve_dep_src_dir):
    """
    Download the module that is imported by the controller and copy it to the controller folder
    because we later need to instrument these modules.

    :param module: the module to download
    :param sieve_dep_src_dir: the dst folder to copy the downloaded module to
    """
    module_src = os.path.join(GOPATH, "pkg/mod", module)
    module_dst = os.path.join(sieve_dep_src_dir, module)
    os_system("go mod download {} >> /dev/null".format(module))
    os.makedirs(os.path.join(sieve_dep_src_dir, os.path.dirname(module)))
    shutil.copytree(
        module_src,
        module_dst,
    )
    add_mod_recursively(module_dst, stat.S_IWRITE)


def install_lib_for_controller(controller_config: ControllerConfig):
    """
    Copy (1) sieve client, (2) client-go and (3) other modules that require instrumentation to the controller folder
    for later instrumentation.

    :param controller_config: the controller configuration
    """
    application_dir = os.path.join("app", controller_config.controller_name)
    sieve_dep_src_dir = os.path.join(
        application_dir,
        "sieve-dependency/src",
    )

    # install sieve_client
    shutil.copytree(
        "sieve_client",
        os.path.join(
            sieve_dep_src_dir,
            "sieve.client",
        ),
    )
    if controller_config.kubernetes_version != DEFAULT_K8S_VERSION:
        update_sieve_client_go_mod_with_version(
            os.path.join(sieve_dep_src_dir, "sieve.client", "go.mod"),
            k8s_version_to_apimachinery_version(controller_config.kubernetes_version),
        )
    elif controller_config.apimachinery_version is not None:
        update_sieve_client_go_mod_with_version(
            os.path.join(sieve_dep_src_dir, "sieve.client", "go.mod"),
            controller_config.apimachinery_version,
        )

    # download client-go
    install_module(
        "k8s.io/client-go@{}".format(controller_config.client_go_version),
        sieve_dep_src_dir,
    )

    # download the other dependencies
    downloaded_module = set()
    for api_to_instrument in controller_config.apis_to_instrument:
        module = api_to_instrument["module"]
        if module in downloaded_module:
            continue
        downloaded_module.add(module)
        install_module(module, sieve_dep_src_dir)

    os.chdir(application_dir)
    os_system("git add -A >> /dev/null")
    os_system('git commit -m "install the lib" >> /dev/null')
    os.chdir(ORIGINAL_DIR)


def remove_replacement_in_go_mod_file(file):
    """
    Remove the existing `k8s.io/client-go => ` in the go.mod of the controller
    because later we will modify the go.mod to import the instrumented client-go.

    :param file: the go.mod file of the controller
    """
    # TODO: we should also remove the replace entry for other instrumented modules
    lines = []
    with open(file, "r") as go_mod_file:
        lines = go_mod_file.readlines()
    with open(file, "w") as go_mod_file:
        for line in lines:
            if "k8s.io/client-go => " in line:
                continue
            go_mod_file.write(line)


def update_go_mod_for_controller(
    controller_config_dir,
    controller_config: ControllerConfig,
):
    """
    Update the go.mod of the controller to import sieve client and the local client-go and other modules.

    :param controller_config_dir: the folder containing the build script provided by controller developers
    :param controller_config: the controller configuration
    """
    application_dir = os.path.join("app", controller_config.controller_name)
    # modify the go.mod to import the libs
    remove_replacement_in_go_mod_file(os.path.join(application_dir, "go.mod"))
    with open("{}/go.mod".format(application_dir), "a") as go_mod_file:
        go_mod_file.write("require sieve.client v0.0.0\n")
        go_mod_file.write(
            "replace sieve.client => ./sieve-dependency/src/sieve.client\n"
        )
        go_mod_file.write(
            "replace k8s.io/client-go => ./sieve-dependency/src/k8s.io/client-go@{}\n".format(
                controller_config.client_go_version
            )
        )
        added_module = set()
        for api_to_instrument in controller_config.apis_to_instrument:
            module = api_to_instrument["module"]
            if module in added_module:
                continue
            added_module.add(module)
            go_mod_file.write(
                "replace {} => ./sieve-dependency/src/{}\n".format(
                    module.split("@")[0], module
                )
            )

    # copy the build.sh and Dockerfile
    shutil.copy(
        os.path.join(controller_config_dir, "build", "build.sh"),
        os.path.join(application_dir, "build.sh"),
    )
    shutil.copy(
        os.path.join(controller_config_dir, "build", "Dockerfile"),
        os.path.join(application_dir, controller_config.dockerfile_path),
    )


def instrument_controller(controller_config: ControllerConfig, mode):
    """
    Instrument the controller source code including client-go and other modules.

    :param controller_config: the controller configuration
    :param mode: the building mode
    """
    application_dir = os.path.join("app", controller_config.controller_name)
    os.chdir("sieve_instrumentation")
    instrumentation_config = {
        "project": controller_config.controller_name,
        "mode": mode,
        "app_file_path": os.path.join(ORIGINAL_DIR, application_dir),
        "client_go_filepath": "{}/{}/sieve-dependency/src/k8s.io/client-go@{}".format(
            ORIGINAL_DIR,
            application_dir,
            controller_config.client_go_version,
        ),
        "annotated_reconcile_functions": controller_config.annotated_reconcile_functions,
        "apis_to_instrument": controller_config.apis_to_instrument,
    }
    json.dump(instrumentation_config, open("config.json", "w"), indent=4)
    os_system("go mod tidy")
    os_system("go build")
    os_system("./instrumentation config.json")
    os.chdir(ORIGINAL_DIR)


def install_lib_for_controller_with_vendor(controller_config: ControllerConfig):
    """
    A variant of install_lib_for_controller for controllers that use vendor.

    :param controller_config: the controller configuration
    """
    application_dir = os.path.join("app", controller_config.controller_name)
    shutil.copytree(
        "sieve_client",
        os.path.join(application_dir, controller_config.vendored_sieve_client_path),
    )
    if controller_config.kubernetes_version != DEFAULT_K8S_VERSION:
        update_sieve_client_go_mod_with_version(
            os.path.join(
                application_dir, controller_config.vendored_sieve_client_path, "go.mod"
            ),
            k8s_version_to_apimachinery_version(controller_config.kubernetes_version),
        )
    elif controller_config.apimachinery_version is not None:
        update_sieve_client_go_mod_with_version(
            os.path.join(
                application_dir, controller_config.vendored_sieve_client_path, "go.mod"
            ),
            controller_config.apimachinery_version,
        )
    os.chdir(application_dir)
    os_system("git add -A >> /dev/null")
    os_system('git commit -m "install the lib" >> /dev/null')
    os.chdir(ORIGINAL_DIR)


def update_go_mod_for_controller_with_vendor(
    controller_config_dir,
    controller_config: ControllerConfig,
):
    """
    A variant of update_go_mod_for_controller for controllers that use vendor.

    :param controller_config_dir: the folder containing the build script provided by controller developers
    :param controller_config: the controller configuration
    """
    application_dir = os.path.join("app", controller_config.controller_name)
    with open(os.path.join(application_dir, "go.mod"), "a") as go_mod_file:
        go_mod_file.write("require sieve.client v0.0.0\n")
    # copy the build.sh and Dockerfile
    shutil.copy(
        os.path.join(controller_config_dir, "build", "build.sh"),
        os.path.join(application_dir, "build.sh"),
    )
    shutil.copy(
        os.path.join(controller_config_dir, "build", "Dockerfile"),
        os.path.join(application_dir, controller_config.dockerfile_path),
    )
    os.chdir(application_dir)
    os_system("git add -A >> /dev/null")
    os_system('git commit -m "import the lib" >> /dev/null')
    os.chdir(ORIGINAL_DIR)


def instrument_controller_with_vendor(controller_config: ControllerConfig, mode):
    """
    A variant of instrument_controller for controllers that use vendor.

    :param controller_config: the controller configuration
    :param mode: the building mode
    """
    application_dir = os.path.join("app", controller_config.controller_name)
    os.chdir("sieve_instrumentation")
    instrumentation_config = {
        "project": controller_config.controller_name,
        "mode": mode,
        "app_file_path": os.path.join(ORIGINAL_DIR, application_dir),
        "client_go_filepath": os.path.join(
            ORIGINAL_DIR,
            application_dir,
            controller_config.vendored_client_go_path,
        ),
        "annotated_reconcile_functions": controller_config.annotated_reconcile_functions,
        "apis_to_instrument": controller_config.apis_to_instrument,
    }
    json.dump(instrumentation_config, open("config.json", "w"), indent=4)
    os_system("go mod tidy")
    os_system("go build")
    os_system("./instrumentation config.json")
    os.chdir(ORIGINAL_DIR)


def build_controller(
    controller_config: ControllerConfig,
    image_tag,
    container_registry,
):
    """
    Build the controller docker image.

    :param controller_config: the controller configuration
    :param container_registry: the name of the container registry as part of the image name
    :param image_tag: the tag of the image
    """
    application_dir = os.path.join("app", controller_config.controller_name)
    os.chdir(application_dir)
    os_system("./build.sh {} {}".format(container_registry, image_tag))
    os.chdir(ORIGINAL_DIR)
    os.system(
        "docker tag {} {}/{}:{}".format(
            controller_config.controller_image_name,
            container_registry,
            controller_config.controller_name,
            image_tag,
        )
    )


def push_controller(
    controller_config: ControllerConfig,
    image_tag,
    container_registry,
):
    """
    Push the controller image to a remote registry.

    :param controller_config: the controller configuration
    :param container_registry: the name of the container registry to push the image to
    :param image_tag: the tag of the image
    """
    os_system(
        "docker push {}/{}:{}".format(
            container_registry,
            controller_config.controller_name,
            image_tag,
        )
    )


def setup_controller(
    controller_config_dir,
    controller_config: ControllerConfig,
    mode,
    image_tag,
    build_only,
    push_to_remote,
    container_registry,
):
    """
    Download the controller, import sieve client, client-go and other modules that require instrumentation,
    build the controller image and push to the remote registry if needed.
    It works for controllers that use mod or vendor.

    :param controller_config_dir: the folder containing the build script provided by the controller developer
    :param controller_config: the controller configuration
    :param mode: the building mode
    :param image_tag: the tag of the image
    :param build_only: if true then directly build the local controller code instead of downloading it
    :param push_to_remote: if true then push the image to container_registry
    :param container_registry: the name of the container registry to push the image to
    """
    if not build_only:
        download_controller(controller_config)
        if controller_config.go_mod == "mod":
            install_lib_for_controller(controller_config)
            update_go_mod_for_controller(controller_config_dir, controller_config)
            instrument_controller(controller_config, mode)
        else:
            install_lib_for_controller_with_vendor(controller_config)
            update_go_mod_for_controller_with_vendor(
                controller_config_dir, controller_config
            )
            instrument_controller_with_vendor(controller_config, mode)
    build_controller(controller_config, image_tag, container_registry)
    if push_to_remote:
        push_controller(controller_config, image_tag, container_registry)


def setup_kubernetes_wrapper(version, mode, container_registry, push_to_remote):
    platform = ""
    # Add a platform tag when building on macOS
    if sys.platform == "darwin":
        platform = "macos-"
    if mode == "all":
        for this_mode in [
            sieve_modes.LEARN,
            sieve_modes.TEST,
            sieve_modes.VANILLA,
        ]:
            image_tag = version + "-" + platform + this_mode
            setup_kubernetes(
                version,
                this_mode,
                container_registry,
                image_tag,
                push_to_remote,
            )
    else:
        image_tag = version + "-" + platform + mode
        setup_kubernetes(version, mode, container_registry, image_tag, push_to_remote)


def setup_controller_wrapper(
    controller_config_dir,
    controller_config: ControllerConfig,
    mode,
    build_only,
    push_to_remote,
    container_registry,
):
    image_tag = mode
    if mode == "all":
        for this_mode in [
            sieve_modes.LEARN,
            sieve_modes.TEST,
            sieve_modes.VANILLA,
        ]:
            image_tag = this_mode
            setup_controller(
                controller_config_dir,
                controller_config,
                this_mode,
                image_tag,
                build_only,
                push_to_remote,
                container_registry,
            )
    else:
        setup_controller(
            controller_config_dir,
            controller_config,
            mode,
            image_tag,
            build_only,
            push_to_remote,
            container_registry,
        )


if __name__ == "__main__":
    common_config = get_common_config()
    usage = "usage: python3 build.py [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option(
        "-c",
        "--controller_config_dir",
        dest="controller_config_dir",
        help="specify the CONTROLLER_CONFIG_DIR",
        metavar="CONTROLLER_CONFIG_DIR",
        default=None,
    )
    parser.add_option(
        "-m",
        "--mode",
        dest="mode",
        help="build MODE: vanilla, learn and test",
        metavar="MODE",
        default=None,
    )
    parser.add_option(
        "-v",
        "--version",
        dest="version",
        help="VERSION of kind image to build",
        metavar="VERSION",
        default=DEFAULT_K8S_VERSION,
    )
    parser.add_option(
        "-s",
        "--sha",
        dest="sha",
        help="commit SHA checksum of the controller to build",
        metavar="SHA",
        default=None,
    )
    parser.add_option(
        "--build_only",
        dest="build_only",
        action="store_true",
        help="build without downloading and instrumenting",
        default=False,
    )
    parser.add_option(
        "-p",
        "--push",
        action="store_true",
        dest="push_to_remote",
        help="push to the container registry",
        default=False,
    )
    parser.add_option(
        "-r",
        "--registry",
        dest="registry",
        help="the container REGISTRY to push the images to",
        metavar="REGISTRY",
        default=common_config.container_registry,
    )
    (options, args) = parser.parse_args()

    if options.mode is None:
        parser.error("parameter mode required")

    if options.mode not in [
        sieve_modes.VANILLA,
        sieve_modes.TEST,
        sieve_modes.LEARN,
        sieve_modes.ALL,
    ]:
        parser.error("invalid build mode option: {}".format(options.mode))

    if options.mode == sieve_modes.ALL and options.build_only:
        parser.error("Building controller docker image for ALL mode not"
                     " supported. Supported modes:  vanilla, learn and test")

    if options.controller_config_dir is None:
        setup_kubernetes_wrapper(
            options.version,
            options.mode,
            options.registry,
            options.push_to_remote,
        )
    else:
        controller_config = load_controller_config(options.controller_config_dir)
        if options.sha is not None:
            controller_config.commit = options.sha
        setup_controller_wrapper(
            options.controller_config_dir,
            controller_config,
            options.mode,
            options.build_only,
            options.push_to_remote,
            options.registry,
        )
