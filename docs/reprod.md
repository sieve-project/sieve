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
[ERROR] persistentvolumeclaim/default/data-volume-cassandra-test-cluster-dc1-rack1-0 DELETE inconsistency: 1 events seen during learning run, but 13 seen during testing run
Checking for cluster resource states...
[ERROR] persistentvolumeclaim TERMINATING inconsistency: 0 seen after learning run, but 1 seen after testing run
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
[ERROR] persistentvolumeclaim/default/data-zookeeper-cluster-0 DELETE inconsistency: 1 events seen during learning run, but 13 seen during testing run
Checking for cluster resource states...
[ERROR] persistentvolumeclaim TERMINATING inconsistency: 0 seen after learning run, but 1 seen after testing run
```

### [pravega-zookeeper-operator-314](https://github.com/pravega/zookeeper-operator/issues/314)
```
python3 sieve.py -p zookeeper-operator -t scaledown-scaleup -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim/default/data-zookeeper-cluster-1 DELETE inconsistency: 1 events seen during learning run, but 5 seen during testing run
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
[ERROR] statefulset/default/rabbitmq-cluster-server CREATE inconsistency: 2 events seen during learning run, but 4 seen during testing run
[ERROR] statefulset/default/rabbitmq-cluster-server DELETE inconsistency: 1 events seen during learning run, but 3 seen during testing run
```

### [K8SPSMDB-430](https://jira.percona.com/browse/K8SPSMDB-430)
```
python3 sieve.py -p mongodb-operator -t recreate -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim/default/mongod-data-mongodb-cluster-rs0-2 DELETE inconsistency: 1 events seen during learning run, but 9 seen during testing run
[ERROR] pod SIZE inconsistency: 4 seen after learning run, but 3 seen after testing run
[ERROR] persistentvolumeclaim SIZE inconsistency: 3 seen after learning run, but 2 seen after testing run
```

### [K8SPSMDB-433](https://jira.percona.com/browse/K8SPSMDB-433)
```
python3 sieve.py -p mongodb-operator -t disable-enable-shard -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] statefulset/default/mongodb-cluster-cfg CREATE inconsistency: 2 events seen during learning run, but 3 seen during testing run
[ERROR] statefulset/default/mongodb-cluster-cfg DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
[ERROR] deployment SIZE inconsistency: 1 seen after learning run, but 2 seen after testing run
[ERROR] pod SIZE inconsistency: 7 seen after learning run, but 8 seen after testing run
```

### [K8SPSMDB-438](https://jira.percona.com/browse/K8SPSMDB-438)
```
python3 sieve.py -p mongodb-operator -t disable-enable-arbiter -d YOUR_DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] statefulset/default/mongodb-cluster-rs0-arbiter CREATE inconsistency: 2 events seen during learning run, but 3 seen during testing run
[ERROR] statefulset/default/mongodb-cluster-rs0-arbiter DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
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

