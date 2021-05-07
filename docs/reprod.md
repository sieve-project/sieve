## Bug Reproduction
This documentation is a little bit stale. We will update it soon.

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
python3 sieve.py -p cassandra-operator -t recreate -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim.terminating inconsistent: learning: 0, testing: 1
[ERROR] persistentvolumeclaim.delete inconsistent: learning: 1, testing: 13
```

### [instaclustr-cassandra-operator-407](https://github.com/instaclustr/cassandra-operator/issues/407)
This one is special. Please build in this way
```
python3 build.py -p cassandra-operator -m time-travel -s bd8077a478997f63862848d66d4912c59e4c46ff -d YOUR_DOCKER_REPO_NAME
```
and then
```
python3 sieve.py -p cassandra-operator -t scaledown-scaleup -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim.size inconsistent: learning: 2, testing: 1
[ERROR] persistentvolumeclaim.delete inconsistent: learning: 1, testing: 2
```

### [pravega-zookeeper-operator-312](https://github.com/pravega/zookeeper-operator/issues/312)
```
python3 sieve.py -p zookeeper-operator -t recreate -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim.delete inconsistent: learning: 1, testing: 13
[ERROR] persistentvolumeclaim.terminating inconsistent: learning: 0, testing: 1
```

### [pravega-zookeeper-operator-314](https://github.com/pravega/zookeeper-operator/issues/314)
```
python3 sieve.py -p zookeeper-operator -t scaledown-scaleup -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim.delete inconsistent: learning: 1, testing: 5
[ERROR] persistentvolumeclaim.terminating inconsistent: learning: 0, testing: 1
[ERROR] pod.terminating inconsistent: learning: 0, testing: 1
```

### [rabbitmq-cluster-operator-648](https://github.com/rabbitmq/cluster-operator/issues/648)
```
python3 sieve.py -p rabbitmq-operator -t recreate -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] statefulset/default/rabbitmq-cluster-server CREATE inconsistency: 2 events seen during normal run, but 3 seen during testing run                                     
[ERROR] statefulset/default/rabbitmq-cluster-server DELETE inconsistency: 1 events seen during normal run, but 2 seen during testing run 
```

### [rabbitmq-cluster-operator-653](https://github.com/rabbitmq/cluster-operator/issues/653)
```
python3 sieve.py -p rabbitmq-operator -t resize-pvc -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] statefulset.delete inconsistent: learning: 1, testing: 3
```

### [K8SPSMDB-430](https://jira.percona.com/browse/K8SPSMDB-430)
```
python3 sieve.py -p mongodb-operator -t recreate -d YOUR_DOCKER_REPO_NAME
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
python3 sieve.py -p cassandra-operator -t scaledown -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will find
```
persistentVolumeClaim has different length: normal: 1 faulty: 2
[FIND BUG] # alarms: 1
```

