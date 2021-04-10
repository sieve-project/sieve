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
Please refer to https://github.com/xlab-uiuc/sonar/issues/54

## Notes:
1. reproduction scripts run typicall slow (may take several minutes to finish one run) because I intentionally add some sleep in the scripts to make sure the controller can finish its job and goes back to stable state before we manipulate its partial history. Sometimes it takes quite long time for a controller to start/delete a pod so the sleep is set to long.
2. [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398) may not always be reproduced because the policy used does not manipulate the timing very well. Currently the bug can be successfully reproduced in more than 90% cases. If not see the expected output, just run it again. **This is a TODO that I will implement a new policy to 100% reproduce [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398) every time.**
3. [instaclustr-cassandra-operator-404](https://github.com/instaclustr/cassandra-operator/issues/404) is a little bit tricky. The controller cannot update the exsiting statefulset as long as the apiserver is paused, but things will get back to normal after the apisever catches up. The existing oracle cannot detect this one well. **This is a TODO that I will implement a better oracle to detect this one.**
4. Some reproduction requires restarting the controller. However, currently the crashing and restarting is done by the workload scripts instead of the sonar server. **This is a TODO that I will implement the mechanism to make the sonar server able to inject crash.**
