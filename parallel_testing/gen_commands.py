import glob
import os
import argparse

patterns = ["intermediate-state", "unobserved-state", "stale-state"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate testcase commands into a file."
    )
    parser.add_argument(
        "-r",
        dest="registry",
        help="Container registry",
        default="ghcr.io/sieve-project/action",
    )
    parser.add_argument(
        "-o", dest="output", help="Output file name", default="commands.txt"
    )
    parser.add_argument("-c", dest="controllers", help="Controllers to test", nargs="+")
    parser.add_argument(
        "--pattern", dest="patterns", help="Patterns to test", nargs="+"
    )
    args = parser.parse_args()

    if args.controllers is None:
        args.controllers = os.listdir("../log")

    if args.patterns is None:
        args.patterns = patterns

    with open(args.output, "w") as command_file, open(
        "pull-commands.txt", "w"
    ) as pull_command_file:
        # pull all k8s images
        pull_command_file.write(
            "docker pull {}/node:v1.18.9-test\n".format(args.docker)
        )
        for controller in args.controllers:
            pull_command_file.write(
                "docker pull {}/{}:test\n".format(args.docker, controller)
            )
            for pattern in args.patterns:
                for test_workload in os.listdir(
                    os.path.join("../sieve_learn_results", controller)
                ):
                    test_plans = glob.glob(
                        os.path.join(
                            os.path.abspath("../sieve_learn_results"),
                            controller,
                            test_workload,
                            "learn",
                            pattern,
                            "*.yaml",
                        )
                    )
                    for test_plan in test_plans:
                        command_file.write(
                            "python3 sieve.py -m test -c {} -w {} -p {} -r {}\n".format(
                                controller,
                                test_workload,
                                test_plan,
                                args.docker,
                            )
                        )
