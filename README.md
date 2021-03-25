# Sonar: Testing Partial History Bugs

## Requirements

* Docker daemon must be running
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
./build.sh -p cassandra-operator -m time-travel
./build.sh -p zookeeper-operator -m time-travel
```

### [instaclustr-cassandra-operator-402](https://github.com/instaclustr/cassandra-operator/issues/402)
```
python3 run.py -p cassandra-operator -t test2 -m compare
```
If reproduced, you will find
```
persistentVolumeClaim has different terminating resources: normal: 0 faulty: 1
[FIND BUG] # alarms: 1
```

### [instaclustr-cassandra-operator-404](https://github.com/instaclustr/cassandra-operator/issues/404)
work in progress

### [instaclustr-cassandra-operator-407](https://github.com/instaclustr/cassandra-operator/issues/407)
```
python3 run.py -p cassandra-operator -t test4 -m compare
```
If reproduced, you will find
```
persistentVolumeClaim has different terminating resources: normal: 0 faulty: 1
[FIND BUG] # alarms: 1
```

### [pravega-zookeeper-operator-312](https://github.com/pravega/zookeeper-operator/issues/312)
```
python3 run.py -p zookeeper-operator -t test1 -m compare
```
If reproduced, you will find
```
persistentVolumeClaim has different terminating resources: normal: 0 faulty: 1
[FIND BUG] # alarms: 1
```

### [pravega-zookeeper-operator-314](https://github.com/pravega/zookeeper-operator/issues/314)
```
python3 run.py -p zookeeper-operator -t test2 -m compare
```
If reproduced, you will find
```
pod has different terminating resources: normal: 0 faulty: 1
persistentVolumeClaim has different terminating resources: normal: 0 faulty: 1
[FIND BUG] # alarms: 2
```

### Observability gaps
First, build the operators:
```
./build.sh -p cassandra-operator -m sparse-read
```

### [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398)
```
python3 run.py -p cassandra-operator -t test1 -m compare
```
If reproduced, you will find
```
persistentVolumeClaim has different length: normal: 1 faulty: 2
[FIND BUG] # alarms: 1
```

### Others
### [instaclustr-cassandra-operator-400](https://github.com/instaclustr/cassandra-operator/issues/400)
This one is not a partial history bug. It can also be reproduced as [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398), but we do not ensure deterministic reproduction since it is caused by randomness in the underlying data structures.


## Notes:
1. reproduction scripts run typicall slow (may take several minutes to finish one run) because I intentionally add some sleep in the scripts to make sure the controller can finish its job and goes back to stable state before we manipulate its partial history. Sometimes it takes quite long time for a controller to start/delete a pod so the sleep is set to long.
2. [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398) may not always be reproduced because the policy used does not manipulate the timing very well. Currently the bug can be successfully reproduced in more than 90% cases. If not see the expected output, just run it again. **This is a TODO that I will implement a new policy to 100% reproduce [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398) every time.**
3. [instaclustr-cassandra-operator-404](https://github.com/instaclustr/cassandra-operator/issues/404) is a little bit tricky. The controller cannot update the exsiting statefulset as long as the apiserver is paused, but things will get back to normal after the apisever catches up. The existing oracle cannot detect this one well. **This is a TODO that I will implement a better oracle to detect this one.**
4. Some reproduction requires restarting the controller. However, currently the crashing and restarting is done by the workload scripts instead of the sonar server. **This is a TODO that I will implement the mechanism to make the sonar server able to inject crash.**
