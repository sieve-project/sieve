# Sieve: Automated Reliability Testing for Kubernetes Controllers

[![License](https://img.shields.io/badge/License-BSD%202--Clause-green.svg)](https://opensource.org/licenses/BSD-2-Clause)
[![Kubernetes Image Build](https://github.com/sieve-project/sieve/actions/workflows/kubernetes.yml/badge.svg)](https://github.com/sieve-project/sieve/actions/workflows/kubernetes.yml)
[![Controller Image Build](https://github.com/sieve-project/sieve/actions/workflows/sieve-controller-image-build.yml/badge.svg)](https://github.com/sieve-project/sieve/actions/workflows/sieve-controller-image-build.yml)
[![Learning Phase](https://github.com/sieve-project/sieve/actions/workflows/sieve-learning-phase.yml/badge.svg)](https://github.com/sieve-project/sieve/actions/workflows/sieve-learning-phase.yml)
[![Bug Reproduction](https://github.com/sieve-project/sieve/actions/workflows/sieve-bug-reproduction.yml/badge.svg)](https://github.com/sieve-project/sieve/actions/workflows/sieve-bug-reproduction.yml)
[![Test](https://github.com/sieve-project/sieve/actions/workflows/sieve-test.yml/badge.svg)](https://github.com/sieve-project/sieve/actions/workflows/sieve-test.yml)


## Sieve
1. [Overview](#overview)
2. [Testing approaches](#testing-approaches)
3. [Pre-requisites for use](#pre-requisites-for-use)
4. [Getting started](#getting-started)
5. [Bugs found by Sieve](#bugs-found-by-sieve)
6. [Learn more](#learn-more)

### Overview
The Kubernetes ecosystem has thousands of controller implementations for different applications and platform capabilities. A controller’s correctness is critical as it manages the application's deployment, scaling and configurations. However, a controller's correctness can be compromised by myriad factors, such as asynchrony, unexpected failures, networking issues, and controller restarts. This in turn can lead to severe safety and liveness violations.

Sieve is a tool to help developers test their controllers by deterministically injecting faults and detecting dormant bugs at development time. Sieve does not require the developers to modify the controller and can reliably reproduce the bugs it finds.

To use Sieve, developers need to port their controllers and provide end-to-end test cases (see [Getting started](#getting-started) for more information). Sieve will automatically instrument the controller by intercepting the event handlers in `client-go` and `controller-runtime`. Sieve runs in two stages. In the learning stage, Sieve will run a test case and identify promising points in an execution to inject faults. It does so by analyzing the sequence of events traced by the instrumented controller. The learning produces test plans that are then executed in the testing stage. A test plan tells Sieve of the type of fault and the point in the execution to inject the fault.

The high-level architecture is shown as below.

<p align="center">
  <img src="https://github.com/sieve-project/sieve/blob/main/docs/sieve-arch.png"  width="70%"/>
</p>

Note that Sieve is an early stage prototype. The tool might not be user-friendly enough due to potential bugs and lack of documentation. We are working hard to address these issues and add new features. Hopefully we will release Sieve as a production-quality software in the near future.

We welcome any users who want to test their controllers using Sieve and we are more than happy to help you port and test your controllers.

### Testing approaches
| Approach                        | Description                                                                                                                                                                                                                                                                                                                                     |
|---------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Intermediate-state Pattern | Intermediate-state Pattern restarts the controller in the middle of its reconcile loop. After restart, the controller will see a partially updated cluster state (i.e., an intermediate state). If the controller fails to recover from the intermediate state, Sieve recognizes it as a bug.                                                            |
| Unobserved-state Pattern    | Unobserved-state pattern manipulates the interleaving between the informer goroutines and the reconciler goroutines in a controller to make the controller miss some particular events received from the apiserver. As controllers are supposed to be fully level-triggered, failing to achieve the desired final state after missing the event indicates a bug. |
| Stale-state Pattern                  | Stale-state pattern aims to find bugs in High-Availability clusters where multiple apiservers are running. It redirects a controller to a relatively stale apiserver. Sieve reports a bug if the controller misbehaves after reading stale cluster state.                                                                                            |

### Pre-requisites for use
* Docker daemon must be running (please ensure you can run `docker` commands without sudo)
* A docker repo that you have write access to
* [python3](https://www.python.org/downloads/) installed
* [go](https://golang.org/doc/install) (preferably 1.13.9) installed and `$GOPATH` set
* [kind](https://kind.sigs.k8s.io/) installed and `$KUBECONFIG` set (Sieve runs tests in a kind cluster)
* [kubectl](https://kubernetes.io/docs/reference/kubectl/kubectl/) installed
* python3 installed and dependency packages installed: run `pip3 install -r requirements.txt`
    <!-- * `kubernetes`, `docker`, `pyyaml`, `jsondiff`, `pysqlite3`, `py-cui`, `docker`, `jsondiff`, `deepdiff` -->
    <!-- * simply run `pip3 install -r requirements.txt` to install all the packages -->
<!-- * [sqlite3](https://help.dreamhost.com/hc/en-us/articles/360028047592-Installing-a-custom-version-of-SQLite3) (>=3.32) installed -->
<!-- Note: sqlite3 is not required if you want to only reproduce the bugs. -->

You can run `python3 check_env.py` to check whether your environment meets the requirement.

### Getting started
Users need to port the controller before testing it with Sieve. Basically, users need to provide the steps to build and deploy the controller and necessary configuration files (e.g., CRD yaml files). We list the detailed porting steps [here](docs/port.md). We are actively working on simplify the porting process.

### Bugs found by Sieve
Sieve has found 46 bugs in 10 different controllers, which are listed [here](docs/bugs.md). We also provide [steps](docs/reprod.md) to reproduce all the intermediate-state/unobserved-states/stale-state bugs found by Sieve. We would appreciate a lot if you mention Sieve and inform us when you report bugs found by Sieve.

### Learn more
You can learn more about Sieve from the following references:

Talks:
* [KubeCon 2021](https://www.youtube.com/watch?v=6JnhjgOaZVk) (27 minutes)
* [HotOS 2021](https://www.youtube.com/watch?v=l1Ze_Xd7gME&list=PLl-7Fg11LUZe_6cCrz6sVvTbE_8SEobNB) (10 minutes)

Research papers:
* Automatic Reliability Testing For Cluster Management Controllers <br>
Xudong Sun, Wenqing Luo, Tyler Gu, Aishwarya Ganesan, Ramnatthan Alagappan, Michael Gasch, Lalith Suresh, and Tianyin Xu. In Proceedings of the 16th USENIX Symposium on Operating Systems Design and Implementation (OSDI'22), Carlsbad, CA, USA, Jul. 2022.
* [Reasoning about modern datacenter infrastructures using partial histories](https://sigops.org/s/conferences/hotos/2021/papers/hotos21-s11-sun.pdf) <br>
Xudong Sun, Lalith Suresh, Aishwarya Ganesan, Ramnatthan Alagappan, Michael Gasch, Lilia Tang, and Tianyin Xu. In Proceedings of the 18th Workshop on Hot Topics in Operating Systems (HotOS-XVIII), Virtual Event, May 2021.
