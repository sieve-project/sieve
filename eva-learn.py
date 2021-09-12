import controllers
import os
import time
import glob


def parse_sieve_log(sieve_log):
    num_configs = "unknwon"
    setup_time = "unknwon"
    total_time = "unknwon"
    for line in open(sieve_log).readlines():
        if line.startswith("Generated") and "config(s)" in line:
            num_configs = line.split(" ")[1]
        if line.startswith("setup time:"):
            setup_time = line.split(" ")[2]
        if line.startswith("total time:"):
            total_time = line.split(" ")[2]
    return num_configs, setup_time, total_time


def evaluate_single(cmd, project, test_suite, mode):
    print("running: %s ..." % cmd)
    s = time.time()
    os.system(cmd)
    total_time = time.time() - s
    generated_config_dir = os.path.join(
        "log", project, test_suite, "learn", mode, "analysis", "gen-" + mode
    )
    num_configs = len(glob.glob(os.path.join(generated_config_dir, "*.yaml")))
    return total_time, num_configs


def evaluate(build):
    eva_dir = "eva"
    os.system("mkdir -p %s" % eva_dir)
    docker_repo_name = sieve_config.config["docker_repo"]
    if build:
        os.system("python3 build.py -p kubernetes -m learn -d %s" % docker_repo_name)
    project_workload_map = controllers.test_suites
    f = open(os.path.join(eva_dir, "output.tsv"), "w")
    for project in project_workload_map.keys():
        if build:
            os.system(
                "python3 build.py -p %s -m learn -d %s" % (project, docker_repo_name)
            )
        for test_suite in project_workload_map[project].keys():
            if project_workload_map[project][test_suite].mode != "time-travel":
                continue
            if project != "mongodb-operator":
                continue

            cmd = "python3 sieve.py -p %s -t %s -d %s -s learn -r" % (
                project,
                test_suite,
                docker_repo_name,
            )
            total_time_with_rl, num_configs_w_rl = evaluate_single(
                cmd, project, test_suite, project_workload_map[project][test_suite].mode
            )

            cmd = "python3 sieve.py -p %s -t %s -d %s -s learn" % (
                project,
                test_suite,
                docker_repo_name,
            )
            total_time, num_configs = evaluate_single(
                cmd, project, test_suite, project_workload_map[project][test_suite].mode
            )

            f.write(
                "%s\t%s\t%s\t%s\t%s\t%s\n"
                % (
                    project,
                    test_suite,
                    total_time,
                    num_configs,
                    total_time_with_rl,
                    num_configs_w_rl,
                )
            )
            f.flush()
    f.close()


if __name__ == "__main__":
    evaluate(False)
