import glob
import os
import argparse

modes = ["intermediate-state", "unobserved-state", "stale-state"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate testcase commands into a file."
    )
    parser.add_argument(
        "-d",
        dest="docker",
        help="Docker account",
        default="ghcr.io/sieve-project/action",
    )
    parser.add_argument(
        "-o", dest="output", help="Output file name", default="commands.txt"
    )
    parser.add_argument("-c", dest="controllers", help="Controllers to test", nargs="+")
    parser.add_argument("-m", dest="modes", help="Modes to test", nargs="+")
    args = parser.parse_args()

    if args.controllers is None:
        controllers = os.listdir("../log")
    else:
        controllers = args.controllers

    if args.modes is not None:
        modes = args.modes

    with open(args.output, "w") as command_file, open(
        "pull-commands.txt", "w"
    ) as pull_command_file:
        # pull all k8s images
        pull_command_file.write(
            "docker pull {}/node:v1.18.9-test\n".format(args.docker)
        )
        pull_command_file.write(
            "docker pull {}/node:v1.18.9-vanilla\n".format(args.docker)
        )
        for controller in controllers:
            pull_command_file.write(
                "docker pull {}/{}:test\n".format(args.docker, controller)
            )
            pull_command_file.write(
                "docker pull {}/{}:vanilla\n".format(args.docker, controller)
            )
            for mode in modes:
                for testcase in os.listdir(os.path.join("../log", controller)):
                    if mode == "vanilla":
                        command_file.write(
                            "python3 sieve.py -m vanilla -c {} -w {} -r {}\n".format(
                                controller, testcase, args.docker
                            )
                        )
                    else:
                        configs = glob.glob(
                            os.path.join(
                                os.path.abspath("../log"),
                                controller,
                                testcase,
                                "generate-oracle/learn.yaml",
                                mode,
                                "*.yaml",
                            )
                        )
                        for config in configs:
                            command_file.write(
                                "python3 sieve.py -m test -c {} -w {} -p {} -r {}\n".format(
                                    controller,
                                    testcase,
                                    config,
                                    args.docker,
                                )
                            )
