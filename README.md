# Sieve: Automated Reliability Testing for Kubernetes Controllers

[![License](https://img.shields.io/badge/License-BSD%202--Clause-green.svg)](https://opensource.org/licenses/BSD-2-Clause)
[![Kubernetes Image Build](https://github.com/sieve-project/sieve/actions/workflows/kubernetes.yml/badge.svg)](https://github.com/sieve-project/sieve/actions/workflows/kubernetes.yml)
[![Controller Image Build](https://github.com/sieve-project/sieve/actions/workflows/sieve-controller-image-build.yml/badge.svg)](https://github.com/sieve-project/sieve/actions/workflows/sieve-controller-image-build.yml)
[![Learning Phase](https://github.com/sieve-project/sieve/actions/workflows/sieve-learning-phase.yml/badge.svg)](https://github.com/sieve-project/sieve/actions/workflows/sieve-learning-phase.yml)
[![Bug Reproduction](https://github.com/sieve-project/sieve/actions/workflows/sieve-bug-reproduction.yml/badge.svg)](https://github.com/sieve-project/sieve/actions/workflows/sieve-bug-reproduction.yml)
[![Test](https://github.com/sieve-project/sieve/actions/workflows/sieve-test.yml/badge.svg)](https://github.com/sieve-project/sieve/actions/workflows/sieve-test.yml)

This is the source code repo for "Automatic Reliability Testing for Cluster Management Controllers" (accepted by OSDI'2022).
We used a different name (Sonar) for the tool in the paper to be anonymous.
This branch is for OSDI'2022 artifact evaluation only.

The entire artifact evaluation process can take about 6 hours if the evaluator runs all the basic instructions and inspects the results.
1. [Getting Started Instructions](#getting-started-instructions)
2. [Detailed Instructions](#detailed-instructions)


## Getting Started Instructions

**We strongly recommend you to use the VM provided by us. This is the VM we used for our evaluation. We have set up the environment and installed all the dependencies on the VM so you can just go ahead to reproduce the results.**

**Note that all the following instructions assume there is only one user running the commands on one machine. Please coordinate between each other to make sure you are not running the commands one the same machine at the same time.**

To use the VM, please run
```
ssh -i your_ssh_private_key ubuntu@vm_hostname
```
Please contact us with your ssh public key and we will add your key to the VM and provide the VM hostname to you.
Note that the ssh public key usually ends with your local hostname.
To be anonymous, you can generate a new ssh key-pair without the hostname by `ssh-keygen -C noname`
or simply delete the hostname at the end of your public key.

After log in, please
```
cd /home/ubuntu/osdi-ae/sieve
```
and follow the instructions to evaluate the artifact.

### Pre-requisites (skip this if using the VM provided by us):
<details>
  <summary>Click to expand!</summary>

* A Linux system with Docker support
* [python3](https://www.python.org/downloads/) installed
* [go](https://golang.org/doc/install) (preferably 1.13.9) installed and `$GOPATH` set
* [kind](https://kind.sigs.k8s.io/) installed and `$KUBECONFIG` set (Sieve runs tests in a kind cluster)
* [kubectl](https://kubernetes.io/docs/reference/kubectl/kubectl/) installed
* python3 installed and dependency packages installed: run `pip3 install -r requirements.txt`

You can run `python3 check_env.py` to check whether your environment meets the requirement.
If all the requirements are met, you will see
```
[OK] golang environment detected
[OK] go version 1.13.9 satisfies the requirement
[OK] environment variable $GOPATH detected
[OK] kubectl detected
[OK] kind detected
[OK] kind version v0.11.1 satisfies the requirement
[OK] environment variable $KUBECONFIG detected
[OK] python module kubernetes detected
[OK] python module docker detected
[OK] python module pyyaml detected
[OK] python module deepdiff detected
[WARN] helm is only required for certain controllers, please ignore the following failure if your controller does not need helm
[OK] helm detected
[WARN] mage is only required for certain controllers, please ignore the following failure if your controller does not need mage
[OK] mage detected
```
</details>

### Run a simple example (~5 minutes)
We prepared a simple example (i.e., reproducing a bug found by Sieve) to help detect any obvious problem during the kick-the-tires phase.
Please run the following command:
```
python3 sieve.py -p rabbitmq-operator -c bug_reproduction_test_plans/rabbitmq-operator-intermediate-state-1.yaml
```
It will take about 5 minutes to finish and you will see
```
2 detected end state inconsistencies as follows
End state inconsistency - object field has a different value: persistentvolumeclaim/default/persistence-rabbitmq-cluster-server-0["spec"]["resources"]["requests"]["storage"] is 15Gi after reference run, but 10Gi after testing run
End state inconsistency - object field has a different value: persistentvolumeclaim/default/persistence-rabbitmq-cluster-server-0["status"]["capacity"]["storage"] is 15Gi after reference run, but 10Gi after testing run

[PERTURBATION DESCRIPTION]
Sieve restarts the controller rabbitmq-operator when the trigger expression trigger1 is satisfied, where
trigger1 is satisfied after the controller rabbitmq-operator issues:
delete statefulset/default/rabbitmq-cluster-server with the 1st occurrence.
```
Otherwise please contact us.

## Detailed Instructions

### Artifact goals
We will reproduce key results from evaluation in section 5.1 and 5.2.
We will reproduce Table 3 and Figure 8 for Sieve.
Given we have been improving Sieve since the OSDI submission,
we will use the most recent code base for the artifact evaluation.
Thus, some numbers obtained from the artifact evaluation (e.g., absolute number of test plans) 
can be slightly different from the numbers in the paper we submitted.
We will use the most recent numbers in the camera-ready version.

### Overview
The entire process of testing a controller with Sieve consists of two steps:
1. generating test plans
2. executing test plans

For step 2, we provide instructions to evaluate it in [Reproducing all the 31 intermediate-, stale-, and unobservable-state bugs (~5 hours)](#reproducing-all-the-31-intermediate--stale--and-unobservable-state-bugs-5-hours) by executing test plans to reproduce the 31  intermediate-, stale-, and unobservable-state bugs. This will reproduce the results in Table 3.

For step 1, we provide instructions to evaluate it in [Generating and reducing test plans (~15 minutes)](#generating-and-reducing-test-plans-15-minutes). This will reproduce the results in Figure 8.

### Explanation of important files and folders
We explain some important files and folders used in artifact evaluation
* `sieve.py`: This is the script for running the entire testing process of a controller
* `reproduce_bugs.py`: It calls `sieve.py` to reproduce bugs found by Sieve.
* `reproduce_test_plan_generation.py`: It calls `sieve.py` to generate the test plans used for finding bugs.
* `bug_reproduction_test_plans/`: It contains all the test plans used for reproducing the bugs found by Sieve; The test plans are used by `reproduce_bugs.py`
* `log_for_learning/`: It contains all the controller trace files used for generating the test plans

### Reproducing all the 31 intermediate-, stale-, and unobservable-state bugs (~5 hours)
We listed all the 31 intermediate-, stale-, and unobservable-state bugs and 8 indirect bugs (in total 39) here: https://github.com/sieve-project/sieve/blob/osdi-ae/bugs.md.

We prepared all the test plans (generated by Sieve) that can consistently reproduce the 31 intermediate-, stale-, and unobservable-state bugs in the `bug_reproduction_test_plans` folder.
We also prepared the `reproduce_bugs.py` script to make it convenient to reproduce all the bugs in one run.
To reproduce all the bugs, run
```
python3 reproduce_bugs.py
```
It will take about 5 hours to finish.
After it finishes, you will find a `bug_reproduction_stats.tsv`:
```
controller	bug	reproduced	test-result-file
cass-operator	intermediate-state-1	True	sieve_test_results/cass-operator-recreate-cass-operator-intermediate-state-1.yaml.json
cass-operator	stale-state-1	True	sieve_test_results/cass-operator-recreate-cass-operator-stale-state-1.yaml.json
cassandra-operator	stale-state-1	True	sieve_test_results/cassandra-operator-recreate-cassandra-operator-stale-state-1.yaml.json
cassandra-operator	stale-state-2	True	sieve_test_results/cassandra-operator-scaledown-scaleup-cassandra-operator-stale-state-2.yaml.json
cassandra-operator	unobserved-state-1	True	sieve_test_results/cassandra-operator-scaledown-scaleup-cassandra-operator-unobserved-state-1.yaml.json
casskop-operator	intermediate-state-1	True	sieve_test_results/casskop-operator-scaledown-to-zero-casskop-intermediate-state-1.yaml.json
casskop-operator	stale-state-1	True	sieve_test_results/casskop-operator-recreate-casskop-stale-state-1.yaml.json
casskop-operator	stale-state-2	True	sieve_test_results/casskop-operator-reducepdb-casskop-stale-state-2.yaml.json
casskop-operator	unobserved-state-1	True	sieve_test_results/casskop-operator-scaledown-to-zero-casskop-unobserved-state-1.yaml.json
mongodb-operator	intermediate-state-1	True	sieve_test_results/mongodb-operator-disable-enable-shard-mongodb-operator-intermediate-state-1.yaml.json
mongodb-operator	intermediate-state-2	True	sieve_test_results/mongodb-operator-run-cert-manager-mongodb-operator-intermediate-state-2.yaml.json
mongodb-operator	stale-state-1	True	sieve_test_results/mongodb-operator-recreate-mongodb-operator-stale-state-1.yaml.json
mongodb-operator	stale-state-2	True	sieve_test_results/mongodb-operator-disable-enable-shard-mongodb-operator-stale-state-2.yaml.json
mongodb-operator	stale-state-3	True	sieve_test_results/mongodb-operator-disable-enable-arbiter-mongodb-operator-stale-state-3.yaml.json
mongodb-operator	unobserved-state-1	True	sieve_test_results/mongodb-operator-disable-enable-arbiter-mongodb-operator-unobserved-state-1.yaml.json
nifikop-operator	intermediate-state-1	True	sieve_test_results/nifikop-operator-change-config-nifikop-intermediate-state-1.yaml.json
rabbitmq-operator	intermediate-state-1	True	sieve_test_results/rabbitmq-operator-resize-pvc-rabbitmq-operator-intermediate-state-1.yaml.json
rabbitmq-operator	stale-state-1	True	sieve_test_results/rabbitmq-operator-recreate-rabbitmq-operator-stale-state-1.yaml.json
rabbitmq-operator	stale-state-2	True	sieve_test_results/rabbitmq-operator-resize-pvc-rabbitmq-operator-stale-state-2.yaml.json
rabbitmq-operator	unobserved-state-1	True	sieve_test_results/rabbitmq-operator-scaleup-scaledown-rabbitmq-operator-unobserved-state-1.yaml.json
xtradb-operator	intermediate-state-1	True	sieve_test_results/xtradb-operator-disable-enable-proxysql-xtradb-operator-intermediate-state-1.yaml.json
xtradb-operator	intermediate-state-2	True	sieve_test_results/xtradb-operator-run-cert-manager-xtradb-operator-intermediate-state-2.yaml.json
xtradb-operator	stale-state-1	True	sieve_test_results/xtradb-operator-recreate-xtradb-operator-stale-state-1.yaml.json
xtradb-operator	stale-state-2	True	sieve_test_results/xtradb-operator-disable-enable-haproxy-xtradb-operator-stale-state-2.yaml.json
xtradb-operator	stale-state-3	True	sieve_test_results/xtradb-operator-disable-enable-proxysql-xtradb-operator-stale-state-3.yaml.json
xtradb-operator	unobserved-state-1	True	sieve_test_results/xtradb-operator-scaleup-scaledown-xtradb-operator-unobserved-state-1.yaml.json
yugabyte-operator	stale-state-1	True	sieve_test_results/yugabyte-operator-disable-enable-tls-yugabyte-operator-stale-state-1.yaml.json
yugabyte-operator	stale-state-2	True	sieve_test_results/yugabyte-operator-disable-enable-tuiport-yugabyte-operator-stale-state-2.yaml.json
yugabyte-operator	unobserved-state-1	True	sieve_test_results/yugabyte-operator-scaleup-scaledown-tserver-yugabyte-operator-unobserved-state-1.yaml.json
zookeeper-operator	stale-state-1	True	sieve_test_results/zookeeper-operator-recreate-zookeeper-operator-stale-state-1.yaml.json
zookeeper-operator	stale-state-2	True	sieve_test_results/zookeeper-operator-scaledown-scaleup-zookeeper-operator-stale-state-2.yaml.json
```

The last column of the tsv file points to the test result json file of each bug reproduction.
To verify whether each bug is correctly reproduced, please refer to https://github.com/sieve-project/sieve/blob/osdi-ae/reproducing_bugs.md for more detailed information.

#### What if I want to reproduce only one bug at a time?
<details>
  <summary>Click to expand!</summary>

If you want to reproduce only one bug, run
```
python3 reproduce_bugs.py -p controller_name -b bug_id
```
For example, to reproduce the first intermediate-state bug of the rabbitmq-operator:
```
python3 reproduce_bugs.py -p rabbitmq-operator -b intermediate-state-1
```
Or, to reproduce the first stale-state bug of the casskop-operator (we called it casskop in the paper):
```
python3 reproduce_bugs.py -p casskop-operator -b stale-state-2
```

Reproducing a single bug can take from 5 to 30 minutes.

Note that reproducing a single bug will not update `bug_reproduction_stats.tsv`.
However, you can check the stdout to see whether the bug is successfully reproduced:
If a bug is reproduced, Sieve will detect common errors/end state inconsistencies/history inconsistencies like:
```
XXX common errors as follows
```
or
```
XXX detected end state inconsistencies as follows
```
or
```
XXX detected history inconsistencies as follows
```
You can also refer to the newly generated `test-result-file` hinted by
```
Please refer to XXX for more detailed information
```

</details>

#### What if I find some of the bugs is not reproduced (i.e., the `reproduced` column is `False`)?
<details>
  <summary>Click to expand!</summary>

If you find some of the bug is not reproduced,
please check whether the corresponding `test-result-file` contains a non-empty `exception_message` field similar as below:
```
Traceback (most recent call last):
  File \"sieve.py\", line 550, in run_test
      setup_cluster(test_context)
  File \"sieve.py\", line 267, in setup_cluster
      setup_kind_cluster(test_context)
  File \"sieve.py\", line 254, in setup_kind_cluster
      cmd_early_exit(
  File \"/home/ubuntu/osdi-ae/sieve/sieve_common/common.py\", line 167, in cmd_early_exit
    raise Exception(
Exception: Failed to execute kind create cluster --image ghcr.io/sieve-project/action/node:v1.18.9-test --config kind_configs/kind-3a-2w.yaml with return code 1
```
If so, it means the [kind cluster](https://kind.sigs.k8s.io/) that Sieve relies on accidentally crashes.
The failure is transient so you can just reproduce that particular bug again (please refer to [What if I want to reproduce only one bug at a time?](#what-if-i-want-to-reproduce-only-one-bug-at-a-time)).

</details>

### Optional: Reproducing indirect bugs (~1 hour)
Optionally, if you also want to reproduce the 8 indirect bugs, please refer to https://github.com/sieve-project/sieve/blob/osdi-ae/reproducing_indirect_bugs.md.

### Generating and reducing test plans (~15 minutes)
Sieve automatically generates test plans from the controller trace.
We prepared all the controller trace generated in our most recent evaluation.
To generate test plans from the controller trace, run
```
python3 reproduce_test_plan_generation.py
```
It will take about 15 minutes to finish.
After it finishes, you will find a `test_plan_stats.tsv`:
```
controller	baseline	prune-by-causality	prune-updates	deterministic-timing
cass-operator	2664	415	415	218
cassandra-operator	152	106	84	81
casskop-operator	580	502	149	125
mongodb-operator	144233	7247	616	584
nifikop-operator	6570	6209	5030	239
rabbitmq-operator	311	261	213	133
xtradb-operator	3944	3404	416	395
yugabyte-operator	1414	970	294	196
zookeeper-operator	38028	14533	2712	164
```

#### Why are the numbers slightly different from the ones presented in Figure 8 in paper?
<details>
  <summary>Click to expand!</summary>

You might find the numbers above are slightly different from the ones we presented in Figure 8 in paper.
The reason is that we are using the most recent code base and controller traces for this artifact evaluation,
and Sieve has been improved a lot by adding features and fixing bugs since the OSDI submission.

We will also use the most recent numbers in the camera-ready version.

</details>

### Optional: Generating controller trace and test plans (~8 hours)
Optionally, you can run the test workload to generate the trace and further generate and reduce the test plans by running
```
python3 reproduce_test_plan_generation.py --log=log --phase=all --times=twice
```
It will take about 8 hours.

The `test_plan_stats.tsv` generated can be slightly different as the controller traces are naturally nondeterministic.
For example, the number of events received by a controller can be different across different runs,
which will affect the number of generated test plans slightly.
