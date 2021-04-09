# Sonar: Testing Partial History Bugs

## Requirements

* Docker daemon must be running
* A docker repo that you have write access to
* go1.13 installed and `$GOPATH` set
* python3 installed and `kubernetes` and `pyyaml` installed (`pip3 install kubernetes` and `pip3 install pyyaml`)

## Bugs Found
[instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398) confirmed and fixed by our patch (observability gaps)

[instaclustr-cassandra-operator-400](https://github.com/instaclustr/cassandra-operator/issues/400) confirmed and fixed by our patch (other)

[instaclustr-cassandra-operator-402](https://github.com/instaclustr/cassandra-operator/issues/402) confirmed and fixed by our patch (time travel)

[instaclustr-cassandra-operator-404](https://github.com/instaclustr/cassandra-operator/issues/404) confirmed and fixed by our patch (time travel)

[instaclustr-cassandra-operator-407](https://github.com/instaclustr/cassandra-operator/issues/407) confirmed (time travel)

[pravega-zookeeper-operator-312](https://github.com/pravega/zookeeper-operator/issues/312) confirmed and fixed by our patch (time travel)

[pravega-zookeeper-operator-314](https://github.com/pravega/zookeeper-operator/issues/314) waiting (time travel)

## Bug Reproduction
### Time travel
First, build the operators:
```
python3 build.py -p kubernetes -m time-travel -d YOUR_DOCKER_REPO_NAME
python3 build.py -p cassandra-operator -m time-travel -d YOUR_DOCKER_REPO_NAME
python3 build.py -p zookeeper-operator -m time-travel -d YOUR_DOCKER_REPO_NAME
python3 build.py -p rabbitmq-operator -m time-travel -d YOUR_DOCKER_REPO_NAME
python3 build.py -p mongodb-operator -m time-travel -d YOUR_DOCKER_REPO_NAME
```
Please specify the `YOUR_DOCKER_REPO_NAME` that you have write access to -- sonar needs to push controller image to the repo.

### [instaclustr-cassandra-operator-402](https://github.com/instaclustr/cassandra-operator/issues/402)
```
python3 run.py -p cassandra-operator -t test2 -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim.terminating inconsistent: learning: 0, testing: 1
[ERROR] persistentvolumeclaim.delete inconsistent: learning: 1, testing: 13
```

### [instaclustr-cassandra-operator-407](https://github.com/instaclustr/cassandra-operator/issues/407)
This one is special. Please build in this way
```
python3 build.py -p cassandra-operator -m time-travel -s 26958ef772dd192d4a7083d04d2a23c8ea821558 -d YOUR_DOCKER_REPO_NAME
```
and then
```
python3 run.py -p cassandra-operator -t test4 -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim.size inconsistent: learning: 2, testing: 1
[ERROR] persistentvolumeclaim.delete inconsistent: learning: 1, testing: 2
```

### [pravega-zookeeper-operator-312](https://github.com/pravega/zookeeper-operator/issues/312)
```
python3 run.py -p zookeeper-operator -t test1 -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim.delete inconsistent: learning: 1, testing: 13
[ERROR] persistentvolumeclaim.terminating inconsistent: learning: 0, testing: 1
```

### [pravega-zookeeper-operator-314](https://github.com/pravega/zookeeper-operator/issues/314)
```
python3 run.py -p zookeeper-operator -t test2 -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim.delete inconsistent: learning: 1, testing: 5
[ERROR] persistentvolumeclaim.terminating inconsistent: learning: 0, testing: 1
[ERROR] pod.terminating inconsistent: learning: 0, testing: 1
```

### [rabbitmq-cluster-operator-648](https://github.com/rabbitmq/cluster-operator/issues/648)
```
python3 run.py -p rabbitmq-operator -t test1 -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] statefulset.create inconsistent: learning: 2, testing: 3
[ERROR] statefulset.delete inconsistent: learning: 1, testing: 2
[ERROR] pod.size inconsistent: learning: 2, testing: 1
```

### [rabbitmq-cluster-operator-653](https://github.com/rabbitmq/cluster-operator/issues/653)
```
python3 run.py -p rabbitmq-operator -t test2 -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] statefulset.delete inconsistent: learning: 1, testing: 3
```

### [K8SPSMDB-430](https://jira.percona.com/browse/K8SPSMDB-430)
```
python3 run.py -p mongodb-operator -t test1 -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] statefulset.create inconsistent: learning: 2, testing: 4
[ERROR] statefulset.delete inconsistent: learning: 1, testing: 2
[ERROR] issuer.create inconsistent: learning: 3, testing: 2
[ERROR] persistentvolumeclaim.delete inconsistent: learning: 3, testing: 25
```

### Observability gaps
First, build the operators:
```
python3 build.py -p kubernetes -m sparse-read -d YOUR_DOCKER_REPO_NAME
python3 build.py -p cassandra-operator -m sparse-read -d YOUR_DOCKER_REPO_NAME
```

### [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398)
```
python3 run.py -p cassandra-operator -t test1 -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will find
```
persistentVolumeClaim has different length: normal: 1 faulty: 2
[FIND BUG] # alarms: 1
```

### By-products
### [instaclustr-cassandra-operator-400](https://github.com/instaclustr/cassandra-operator/issues/400)
This one is not a partial history bug. It can also be reproduced as [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398), but we do not ensure deterministic reproduction since it is caused by randomness in the underlying data structures.


## Port a new operator:
In general, you will need to fill the entries in https://github.com/xlab-uiuc/sonar/blob/main/controllers.py and prepare some Dockerfile, build scripts, deploy scripts and test scripts.

### Build
The first thing is to be able to build the operator into a container image and make sure the operator can function well.
Oftentimes, you will find how to build the operator in the readme or developer documentation.
The image build command is often in their Makefile, and you can easily find the Dockerfile.
What you need to do is to slightly modify the Dockerfile to:
1. Set the initial CMD as `["sleep", "infinity"]`. See [zookeeper-operator](https://github.com/xlab-uiuc/sonar/blob/1606d324c509f0d4841629e3107ce78cc0e324cb/test-zookeeper-operator/build/Dockerfile#L40).
2. Install bash (or other necessary tools for you) in the image. See [zookeeper-operator](https://github.com/xlab-uiuc/sonar/blob/1606d324c509f0d4841629e3107ce78cc0e324cb/test-zookeeper-operator/build/Dockerfile#L38).
3. If the orignal Dockerfile sets some user account/permission stuff, remove them to make your life easier.

Besides, you need to prepare a `build.sh` which contains all the commands to build an image and push it to your docker repo.
As an example, here is the modified Dockerfile and `build.sh` for the rabbitmq-operator: https://github.com/xlab-uiuc/sonar/tree/main/test-rabbitmq-operator/build.
Your Dockerfile will replace the original one, and the `build.sh` will be run in the operator directory to build the image. These are done by `build.py`, and you only need to specify related entries in `controllers.py`. Instrumentation will also be automatically done by `build.py` according to the mode you specify.

### Deploy
The second step is to be able to deploy (or install) the (instrumented) operator in your kind cluster.
Sometimes manual deploy steps are clearly listed in the readme (e.g., https://github.com/pravega/zookeeper-operator#manual-deployment) and you just need to type them one by one,
while sometimes you need to read the developer documentation to find out how to deploy the operator.
Concretely, deploying the operator often consists of:
1. Installing the CRDs and related RBAC config. For example, `kubectl create -f deploy/crds` and `kubectl create -f deploy/default_ns/rbac.yaml` for the [zookeeper-operator](https://github.com/pravega/zookeeper-operator).
2. Starting the deployment of the operator. For example, `kubectl create -f deploy/default_ns/operator.yaml` for the [zookeeper-operator](https://github.com/pravega/zookeeper-operator).

For a new controller, you need to find the correct commands (and configs) to do the above.
Besides, you also need to modify the deployment config of the operator to do the following:
1. Add a label: `sonartag: YOUR_OPERATOR_NAME`. So sonar can later find the pod.
2. Replace the operator image repo name with `${SONAR-DR}`, and replace the tag with `${SONAR-DT}`. So sonar can use correct repo and tag when running the tests.
3. If `command` is specified, remove it. So sonar we can decide when to start/stop the operator without breaking the pod.

See https://github.com/xlab-uiuc/sonar/blob/main/test-zookeeper-operator/deploy/default_ns/operator.yaml as an example.
After figuring out how to deploy the operator, write them down in `controllers.py` as the [zookeeper-operator](https://github.com/xlab-uiuc/sonar/blob/32c003016cb95e05487b9609115efa6325a36606/controllers.py#L155).

### Test
The final step is to prepare the test workloads, and sonar learn mode will automatically generate the time-travel config for the workload. The workload is often simple -- create/delete/create some resources, scale down/up some resources, or disable/enable some features in the spec. See https://github.com/xlab-uiuc/sonar/blob/main/test-zookeeper-operator/test/recreateZookeeperCluster.sh and https://github.com/xlab-uiuc/sonar/blob/main/test-zookeeper-operator/test/scaleDownUpZookeeperCluster.sh as examples.
Note that it takes some time for the operator to process one command so we sleep for a while before each command. The sleep time is set empirically.
Operator usually runs more slowly in learning mode, so we sometimes set larger sleep time in learning mode as in [zookeeper-operator](https://github.com/xlab-uiuc/sonar/blob/32c003016cb95e05487b9609115efa6325a36606/test-zookeeper-operator/test/recreateZookeeperCluster.sh#L6).
Try to run the vanilla operator to decide the sleep time here. It usually ranges from 30s to 1 min. We may later find a better way to decide the sleep time.

After writing the workload, register it in `controllers.py` like the [zookeeper-operator](https://github.com/xlab-uiuc/sonar/blob/32c003016cb95e05487b9609115efa6325a36606/controllers.py#L53).
After that, build the learning mode images
```
python3 build.py -p kubernetes -m learn -d YOUR_DOCKER_REPO_NAME
python3 build.py -p YOUR_OPERATOR_NAME -m learn -d YOUR_DOCKER_REPO_NAME
```
Run the learning mode
```
python3 run.py -p YOUR_OPERATOR_NAME -m learn -t YOUR_TEST_NAME
```
You will get some config files generated by sonar in `log/YOUR_OPERATOR_NAME/YOUR_TEST_NAME/learn/generated-config`.
To test them all, run
```
python3 run.py -p YOUR_OPERATOR_NAME -t YOUR_TEST_NAME -b
```
to test one of them (which you think is more promising)
```
python3 run.py -p YOUR_OPERATOR_NAME -t YOUR_TEST_NAME -c YOUR_FAVOURITE_CONFIG
```
Usually, if you can see `[ERROR]` in stdout, it indicates a bug.

## Notes:
1. reproduction scripts run typicall slow (may take several minutes to finish one run) because I intentionally add some sleep in the scripts to make sure the controller can finish its job and goes back to stable state before we manipulate its partial history. Sometimes it takes quite long time for a controller to start/delete a pod so the sleep is set to long.
2. [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398) may not always be reproduced because the policy used does not manipulate the timing very well. Currently the bug can be successfully reproduced in more than 90% cases. If not see the expected output, just run it again. **This is a TODO that I will implement a new policy to 100% reproduce [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398) every time.**
3. [instaclustr-cassandra-operator-404](https://github.com/instaclustr/cassandra-operator/issues/404) is a little bit tricky. The controller cannot update the exsiting statefulset as long as the apiserver is paused, but things will get back to normal after the apisever catches up. The existing oracle cannot detect this one well. **This is a TODO that I will implement a better oracle to detect this one.**
4. Some reproduction requires restarting the controller. However, currently the crashing and restarting is done by the workload scripts instead of the sonar server. **This is a TODO that I will implement the mechanism to make the sonar server able to inject crash.**
