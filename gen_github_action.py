#!/usr/bin/env python3
from reproduce_bugs import reprod_map
import yaml
import os
from sieve_common.common import sieve_modes
from datetime import datetime

operators_for_CI = {
    "cassandra-operator": ["recreate", "scaledown-scaleup"],
    "zookeeper-operator": ["recreate", "scaledown-scaleup"],
    "rabbitmq-operator": ["recreate", "scaleup-scaledown", "resize-pvc"],
    "mongodb-operator": [
        "recreate",
        "scaleup-scaledown",
        "disable-enable-shard",
        "disable-enable-arbiter",
        "run-cert-manager",
    ],
    "cass-operator": ["recreate", "scaledown-scaleup"],
    "casskop-operator": ["recreate", "scaledown-to-zero", "reducepdb"],
    "xtradb-operator": [
        "recreate",
        "disable-enable-haproxy",
        "disable-enable-proxysql",
        "run-cert-manager",
        "scaleup-scaledown",
    ],
    "yugabyte-operator": [
        "recreate",
        "scaleup-scaledown-tserver",
        "disable-enable-tls",
        "disable-enable-tuiport",
    ],
    "nifikop-operator": ["recreate", "scaledown-scaleup", "change-config"],
}


def generate_jobs(ci_mode):
    jobs = {}

    for operator in reprod_map:
        if operator not in operators_for_CI:
            continue
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
                    "run": 'echo "{\\"workload_hard_timeout\\": 1000}" > sieve_config.json\ncat sieve_config.json',
                },
            ],
        }
        collect_log = {
            "uses": "actions/upload-artifact@v2",
            "if": "always()",
            "with": {"name": "sieve-%s-log" % (operator), "path": "log"},
        }
        persistent_data = {
            "uses": "JamesIves/github-pages-deploy-action@4.1.5",
            "name": "Persistent oracle data",
            "with": {
                "branch": "oracle-data",
                "folder": "examples/%s/oracle" % (operator),
                "target-folder": "%s/oracle" % (operator),
            },
        }
        remove_cluster = {
            "name": "Remove cluster",
            "if": "always()",
            "run": "kind delete cluster",
        }
        clean_images = {
            "name": "Clean images",
            "if": "always()",
            "run": "docker image prune -a -f && docker builder prune -a -f && docker system df",
        }

        build_modes = [
            "learn",
            "test",
            sieve_modes.VANILLA,
        ]
        workload_set = set()

        for bug in reprod_map[operator]:
            if "indirect" in bug:
                continue
            workload = reprod_map[operator][bug][0]
            config_name = reprod_map[operator][bug][1]
            config = yaml.safe_load(
                open(os.path.join("bug_reproduction_test_plans", config_name)).read()
            )
            workload_set.add(workload)

        for workload in operators_for_CI[operator]:
            workload_set.add(workload)

        build_image = [
            {
                "name": "Build Image - %s" % (mode),
                "run": "python3 build.py -p %s -m %s -d $IMAGE_NAMESPACE"
                % (operator, mode)
                + (" -r" if ci_mode == "daily" else ""),
            }
            for mode in build_modes
        ]
        job["steps"].extend(build_image)

        if not (ci_mode in ["test"] and operator == "xtradb-operator"):
            sieve_learn = [
                {
                    "name": "Sieve Learn - %s %s" % (operator, workload),
                    "run": "python3 sieve.py -p %s -t %s -s learn -m learn-twice -d $IMAGE_NAMESPACE"
                    % (operator, workload),
                }
                for workload in sorted(workload_set)
            ]
            sieve_test = []
            for bug in sorted(reprod_map[operator].keys()):
                if "indirect" in bug:
                    continue
                sieve_test.append(
                    {
                        "name": "Sieve Test - %s %s" % (operator, bug),
                        "run": "python3 reproduce_bugs.py -p %s -b %s -d $IMAGE_NAMESPACE"
                        % (operator, bug),
                    }
                )
            job["steps"].extend(sieve_learn)
            job["steps"].extend(sieve_test)
            job["steps"].append(collect_log)
            job["steps"].append(remove_cluster)
            if ci_mode == "daily":
                job["steps"].append(persistent_data)
                job["steps"].append(clean_images)
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
    "on": {"workflow_dispatch": None, "schedule": [{"cron": "0 6 * * *"}]},
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
