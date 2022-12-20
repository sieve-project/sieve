#!/usr/bin/env python3
from reproduce_bugs import reprod_map
import yaml
import os
from sieve_common.common import sieve_modes
from datetime import datetime

operators_for_CI = {
    "cass-operator": ["recreate", "scaledown-scaleup"],
    "cassandra-operator": ["recreate", "scaledown-scaleup"],
    "casskop-operator": ["recreate", "scaledown-to-zero", "reducepdb"],
    "elastic-operator": ["recreate", "scaledown-scaleup"],
    "mongodb-operator": [
        "recreate",
        "scaleup-scaledown",
        "disable-enable-shard",
        "disable-enable-arbiter",
        "run-cert-manager",
    ],
    "nifikop-operator": ["recreate", "scaledown-scaleup", "change-config"],
    "rabbitmq-operator": ["recreate", "scaleup-scaledown", "resize-pvc"],
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
    "zookeeper-operator": ["recreate", "scaledown-scaleup"],
}

operators_to_run_tests = [
    "cass-operator",
    # "cassandra-operator",
    "casskop-operator",
    "elastic-operator",
    "mongodb-operator",
    # "nifikop-operator",
    "rabbitmq-operator",
    # "xtradb-operator",
    # "yugabyte-operator",
    "zookeeper-operator",
]

manifest_map = {
    "cass-operator": "examples/cass-operator/",
    "cassandra-operator": "examples/cassandra-operator/",
    "casskop-operator": "examples/casskop-operator/",
    "elastic-operator": "examples/elastic-operator/",
    "mongodb-operator": "examples/mongodb-operator/",
    "nifikop-operator": "examples/nifikop-operator/",
    "rabbitmq-operator": "examples/rabbitmq-operator/",
    "xtradb-operator": "examples/xtradb-operator/",
    "yugabyte-operator": "examples/yugabyte-operator/",
    "zookeeper-operator": "examples/zookeeper-operator/",
}


def job_template(self_hosted):
    return {
        "runs-on": "self-hosted" if self_hosted else "ubuntu-latest",
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
            {
                "name": "Install Kind",
                "run": 'GO111MODULE="on" go get sigs.k8s.io/kind@v0.13.0\nkind',
            },
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
                "run": 'echo "{\\"workload_conditional_wait_timeout\\": 1000}" > sieve_config.json\ncat sieve_config.json',
            },
        ],
    }


def collect_log_step(operator):
    return {
        "uses": "actions/upload-artifact@v2",
        "if": "always()",
        "with": {"name": "sieve-%s-log" % (operator), "path": "log"},
    }


def persistent_data_step(operator):
    return {
        "uses": "JamesIves/github-pages-deploy-action@4.1.5",
        "name": "Persistent oracle data",
        "with": {
            "branch": "oracle-data",
            "folder": "examples/%s/oracle" % (operator),
            "target-folder": "%s/oracle" % (operator),
        },
    }


def remove_cluster_step():
    return {
        "name": "Remove cluster",
        "if": "always()",
        "run": "kind delete cluster",
    }


def clean_images_step():
    return {
        "name": "Clean images",
        "if": "always()",
        "run": "docker image prune -a -f && docker builder prune -a -f && docker system df",
    }


def generate_controller_image_build_jobs(self_hosted):
    jobs = {}
    for operator in operators_for_CI:
        job = job_template(self_hosted)
        build_modes = [
            sieve_modes.LEARN,
            sieve_modes.TEST,
            sieve_modes.VANILLA,
        ]
        build_image = [
            {
                "name": "Build Image - %s" % (mode),
                "run": "python3 build.py -c %s -m %s -p -r $IMAGE_NAMESPACE "
                % (manifest_map[operator], mode),
            }
            for mode in build_modes
        ]
        job["steps"].extend(build_image)
        job["steps"].append(clean_images_step())
        jobs[operator] = job
    return jobs


def generate_oracle_build_jobs(self_hosted):
    jobs = {}
    for operator in operators_for_CI:
        job = job_template(self_hosted)
        workload_set = set(operators_for_CI[operator])
        sieve_learn = [
            {
                "name": "Sieve Learn - %s %s" % (operator, workload),
                "run": "python3 sieve.py -c %s -w %s -m generate-oracle -r $IMAGE_NAMESPACE"
                % (manifest_map[operator], workload),
            }
            for workload in sorted(workload_set)
        ]
        job["steps"].extend(sieve_learn)
        job["steps"].append(collect_log_step(operator))
        job["steps"].append(remove_cluster_step())
        job["steps"].append(persistent_data_step(operator))
        job["steps"].append(clean_images_step())
        jobs[operator] = job
    return jobs


def generate_bug_reproduction_jobs(self_hosted):
    jobs = {}
    for operator in operators_for_CI:
        job = job_template(self_hosted)
        sieve_test = []
        for bug in sorted(reprod_map[operator].keys()):
            if "indirect" in bug:
                continue
            sieve_test.append(
                {
                    "name": "Sieve Test - %s %s" % (operator, bug),
                    "run": "python3 reproduce_bugs.py -c %s -b %s -r $IMAGE_NAMESPACE"
                    % (operator, bug),
                }
            )
        job["steps"].extend(sieve_test)
        job["steps"].append(collect_log_step(operator))
        job["steps"].append(remove_cluster_step())
        job["steps"].append(persistent_data_step(operator))
        job["steps"].append(clean_images_step())
        jobs[operator] = job
    return jobs


def generate_test_jobs(self_hosted):
    jobs = {}
    for operator in operators_for_CI:
        job = job_template(self_hosted)
        build_modes = [
            sieve_modes.LEARN,
            sieve_modes.TEST,
            sieve_modes.VANILLA,
        ]
        workload_set = set(operators_for_CI[operator])
        build_image = [
            {
                "name": "Build Image - %s" % (mode),
                "run": "python3 build.py -c %s -m %s -r $IMAGE_NAMESPACE"
                % (manifest_map[operator], mode),
            }
            for mode in build_modes
        ]
        job["steps"].extend(build_image)
        if operator in operators_to_run_tests:
            sieve_learn = [
                {
                    "name": "Sieve Learn - %s %s" % (operator, workload),
                    "run": "python3 sieve.py -c %s -w %s -m generate-oracle -r $IMAGE_NAMESPACE"
                    % (manifest_map[operator], workload),
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
                        "run": "python3 reproduce_bugs.py -c %s -b %s -r $IMAGE_NAMESPACE"
                        % (operator, bug),
                    }
                )
            job["steps"].extend(sieve_learn)
            job["steps"].extend(sieve_test)
            job["steps"].append(collect_log_step(operator))
            job["steps"].append(remove_cluster_step())
        jobs[operator] = job
    return jobs


open(".github/workflows/regression-testing.yml", "w").write(
    "# This file is automatically generated by gen_github_action.py on %s\n"
    % (datetime.now())
    + yaml.dump(
        {
            "name": "Regression Testing",
            "on": {"pull_request": None, "workflow_dispatch": None},
            "env": {"IMAGE_NAMESPACE": "ghcr.io/sieve-project/action"},
            "jobs": generate_test_jobs(False),
        },
        default_flow_style=False,
        sort_keys=False,
        width=1000,
    )
)

open(".github/workflows/example-controller-image-build.yml", "w").write(
    "# This file is automatically generated by gen_github_action.py on %s\n"
    % (datetime.now())
    + yaml.dump(
        {
            "name": "Example Controller Image Build",
            # "on": {"workflow_dispatch": None, "schedule": [{"cron": "0 6 * * *"}]},
            "on": {"workflow_dispatch": None},
            "env": {"IMAGE_NAMESPACE": "ghcr.io/sieve-project/action"},
            "jobs": generate_controller_image_build_jobs(False),
        },
        default_flow_style=False,
        sort_keys=False,
        width=1000,
    )
)

open(".github/workflows/oracle-generation.yml", "w").write(
    "# This file is automatically generated by gen_github_action.py on %s\n"
    % (datetime.now())
    + yaml.dump(
        {
            "name": "Oracle Generation",
            "on": {"workflow_dispatch": None},
            "env": {"IMAGE_NAMESPACE": "ghcr.io/sieve-project/action"},
            "jobs": generate_oracle_build_jobs(True),
        },
        default_flow_style=False,
        sort_keys=False,
        width=1000,
    )
)

open(".github/workflows/bug-reproduction.yml", "w").write(
    "# This file is automatically generated by gen_github_action.py on %s\n"
    % (datetime.now())
    + yaml.dump(
        {
            "name": "Bug Reproduction",
            "on": {"workflow_dispatch": None},
            "env": {"IMAGE_NAMESPACE": "ghcr.io/sieve-project/action"},
            "jobs": generate_bug_reproduction_jobs(True),
        },
        default_flow_style=False,
        sort_keys=False,
        width=1000,
    )
)
