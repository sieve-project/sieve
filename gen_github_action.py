#!/usr/bin/env python3
from reprod import reprod_map
import yaml
import os
from common import sieve_modes
from datetime import datetime
import copy


def generate_jobs(ci_mode):
    jobs = {}

    for operator in reprod_map:
        job = {
            "runs-on": "ubuntu-latest" if ci_mode == "test" else "self-hosted",
            "env": {
                "GOPATH": "/home/runner/go",
                "KUBECONFIG": "/home/runner/.kube/config",
            },
            "steps": [
                {"uses": "actions/checkout@v2"},
                {
                    "name": "Setup Git",
                    "run": 'git config --global user.name "sieve"\ngit config --global user.email "sieve@sieve.com"',
                },
                {
                    "name": "Setup Go environment",
                    "uses": "actions/setup-go@v2.1.3",
                    "with": {"go-version": 1.15},
                },
                {
                    "name": "Setup Python",
                    "uses": "actions/setup-python@v2.2.2",
                    "with": {"python-version": 3.7},
                },
                {
                    "name": "Setup GitHub Package Registry",
                    "run": 'echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u "${{ github.actor }}" --password-stdin',
                },
                {
                    "name": "Install Python Packages",
                    "run": "pip install -r requirements.txt",
                },
                {"name": "Install Kind", "run": "go get sigs.k8s.io/kind\nkind"},
                {
                    "name": "Install Mage",
                    "run": "go get -u github.com/magefile/mage\nmage -h",
                },
                {
                    "name": "Install Helm",
                    "run": "wget https://get.helm.sh/helm-v3.6.0-linux-amd64.tar.gz\ntar -zxvf helm-v3.6.0-linux-amd64.tar.gz\nsudo mv linux-amd64/helm /usr/local/bin/helm\nhelm",
                },
                {
                    "name": "Sieve CI config generate",
                    "run": 'echo "{\\"workload_wait_hard_timeout\\": 600}" > sieve_config.json\ncat sieve_config.json',
                },
            ],
        }
        collect_resources = {
            "uses": "actions/upload-artifact@v2",
            "with": {
                "name": "sieve-%s-data" % (operator),
                "path": "data/%s" % (operator),
            },
        }
        collect_log = {
            "uses": "actions/upload-artifact@v2",
            "with": {"name": "sieve-%s-log" % (operator), "path": "log"},
        }

        build_modes = [
            "learn",
            sieve_modes.TIME_TRAVEL,
            sieve_modes.OBS_GAP,
            sieve_modes.ATOM_VIO,
        ]
        workload_set = set()

        for bug in reprod_map[operator]:
            workload = reprod_map[operator][bug][0]
            config_name = reprod_map[operator][bug][1]
            config = yaml.safe_load(open(os.path.join("reprod", config_name)).read())
            workload_set.add(workload)
        #         print(operator, bug, workload, config['mode'])

        build_image = [
            {
                "name": "Build Image - %s" % (mode),
                "run": "python3 build.py -p %s -m %s -d $IMAGE_NAMESPACE"
                % (operator, mode),
            }
            for mode in build_modes
        ]
        job["steps"].extend(build_image)

        if not (ci_mode == "test" and operator == "xtradb-operator"):
            sieve_learn = [
                {
                    "name": "Sieve Learn - %s %s" % (operator, workload),
                    "run": "python3 sieve.py -p %s -t %s -s learn -m learn-twice -d $IMAGE_NAMESPACE"
                    % (operator, workload),
                }
                for workload in workload_set
            ]
            sieve_test = [
                {
                    "name": "Sieve Test - %s %s" % (operator, bug),
                    "run": "python3 reprod.py -p %s -b %s -d $IMAGE_NAMESPACE"
                    % (operator, bug),
                }
                for bug in reprod_map[operator].keys()
            ]
            job["steps"].extend(sieve_learn)
            job["steps"].append(collect_resources)
            job["steps"].extend(sieve_test)
            job["steps"].append(collect_log)
        jobs[operator] = job
    return jobs


jobs_test = generate_jobs("test")
config_test = {
    "name": "Sieve Test",
    "on": {"pull_request": None, "workflow_dispatch": None},
    "env": {"IMAGE_NAMESPACE": "ghcr.io/sieve-project/action"},
    "jobs": jobs_test,
}

jobs_daily = generate_jobs("daily")
config_daily = {
    "name": "Sieve Daily Integration",
    "on": {"workflow_dispatch": None, "schedule": [{"cron": "0 4 * * *"}]},
    "env": {"IMAGE_NAMESPACE": "ghcr.io/sieve-project/action"},
    "jobs": jobs_daily,
}

# dump
config_path_test = ".github/workflows/sieve-test.yml"
config_path_daily = ".github/workflows/sieve-daily.yml"
open(config_path_test, "w").write(
    "# This file is automatically generated by gen_github_action.py on %s\n"
    % (datetime.now())
    + yaml.dump(config_test, default_flow_style=False, sort_keys=False)
)
print("CI config generated to %s" % (config_path_test))
open(config_path_daily, "w").write(
    "# This file is automatically generated by gen_github_action.py on %s\n"
    % (datetime.now())
    + yaml.dump(config_daily, default_flow_style=False, sort_keys=False)
)
print("CI config generated to %s" % (config_path_daily))
