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

## Getting Started Instructions

**We strongly recommend you to use the VM provided by us. This is the VM we used for our evaluation. We have set up the environment and installed all the dependencies on the VM so you can just go ahead to reproduce the results.**

### Pre-requisites:
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


### Run a simple example (reproduce a bug found by Sieve)
To run a simple example and detect any obvious problem during the kick-the-tires phase, please run the following command in this `sieve` directory:
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
Otherwise, please contact us.

## Detailed Instructions
We provide detailed instructions to evaluate the following claims in the paper:
TODO

### Explanation of parameters and file names
We explain some important files and folders used in artifact evaluation
* `sieve.py`: This is the script for running the entire testing process of a controller
* `reproduce_bugs.py`: It calls `sieve.py` to reproduce bugs found by Sieve.
* `reproduce_test_plan_generation.py`: It calls `sieve.py` to generate the test plans used for finding bugs.
* `bug_reproduction_test_plans/`: It contains all the test plans used for reproducing the bugs found by Sieve; The test plans are used by `reproduce_bugs.py`
* `log_for_learning/`: It contains all the controller trace files used for generating the test plans

### Reproducing all the 31 intermediate-, stale-, and unobservable-state bugs
We prepared all the test plans (generated by Sieve) that can reproduce the 31 bugs in the `bug_reproduction_test_plans` folder.
We also prepared the `reproduce_bugs.py` script to make it convenient to reproduce all the bugs in one run.
To reproduce all the bugs, run
```
python3 reproduce_bugs.py
```
It will take about 5 hours to finish.

### Generating and reducing test plans
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
Optionally, you can also run the test workload to generate the trace and the test plans by running
```
python3 reproduce_test_plan_generation.py --log=log --phase=all --times=twice
```
It will take about 8 hours.
The `test_plan_stats.tsv` generated can be slightly different as the controller trace can be different.
