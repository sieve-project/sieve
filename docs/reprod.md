## Bug Reproduction

**Before reproducing the bugs, please ensure your local environment meets all the [requirements](https://github.com/sieve-project/sieve#requirements) otherwise Sieve may not work.**

### Time travel
First, build the operators:
```
python3 build.py -p kubernetes -m time-travel -d DOCKER_REPO_NAME
python3 build.py -p cassandra-operator -m time-travel -d DOCKER_REPO_NAME
python3 build.py -p zookeeper-operator -m time-travel -d DOCKER_REPO_NAME
python3 build.py -p rabbitmq-operator -m time-travel -d DOCKER_REPO_NAME
python3 build.py -p mongodb-operator -m time-travel -d DOCKER_REPO_NAME
python3 build.py -p xtradb-operator -m time-travel -d DOCKER_REPO_NAME
python3 build.py -p cass-operator -m time-travel -d DOCKER_REPO_NAME
python3 build.py -p casskop-operator -m time-travel -d DOCKER_REPO_NAME
python3 build.py -p yugabyte-operator -m time-travel -d DOCKER_REPO_NAME
```
Please specify the `DOCKER_REPO_NAME` that you have write access to as sieve needs to push controller image to the repo.

The above commands will download, instrument and build Kubernetes and controller images used for testing.
For Kubernetes, we use the branch `v1.18.9`.
For each controller, we use a default commit SHA specified in `controllers.py`. You can also specify which commit of the operator you want to test by `-s COMMIT_SHA`, but the bugs may not be reproduced with other commits as some of them have been fixed after our reports.

### [instaclustr-cassandra-operator-402](https://github.com/instaclustr/cassandra-operator/issues/402)
```
python3 sieve.py -p cassandra-operator -t recreate -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim/default/data-volume-cassandra-test-cluster-dc1-rack1-0 DELETE inconsistency: 1 events seen during learning run, but 13 seen during testing run
Checking for cluster resource states...
[ERROR] persistentvolumeclaim TERMINATING inconsistency: 0 seen after learning run, but 1 seen after testing run
```
The bug was found in commit `fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd`.

### [instaclustr-cassandra-operator-407](https://github.com/instaclustr/cassandra-operator/issues/407)
This one is special. Please build in this way
```
python3 build.py -p cassandra-operator -m time-travel -s bd8077a478997f63862848d66d4912c59e4c46ff -d DOCKER_REPO_NAME
```
and then
```
python3 sieve.py -p cassandra-operator -t scaledown-scaleup -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim TERMINATING inconsistency: 0 seen after learning run, but 1 seen after testing run
```
The bug was found in commit `bd8077a478997f63862848d66d4912c59e4c46ff`.

### [pravega-zookeeper-operator-312](https://github.com/pravega/zookeeper-operator/issues/312)
```
python3 sieve.py -p zookeeper-operator -t recreate -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim/default/data-zookeeper-cluster-0 DELETE inconsistency: 1 events seen during learning run, but 13 seen during testing run
Checking for cluster resource states...
[ERROR] persistentvolumeclaim TERMINATING inconsistency: 0 seen after learning run, but 1 seen after testing run
```
The bug was found in commit `cda03d2f270bdfb51372192766123904f6d88278`.

### [pravega-zookeeper-operator-314](https://github.com/pravega/zookeeper-operator/issues/314)
```
python3 sieve.py -p zookeeper-operator -t scaledown-scaleup -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim/default/data-zookeeper-cluster-1 DELETE inconsistency: 1 events seen during learning run, but 5 seen during testing run
```
The bug was found in commit `cda03d2f270bdfb51372192766123904f6d88278`.

### [rabbitmq-cluster-operator-648](https://github.com/rabbitmq/cluster-operator/issues/648)
```
python3 sieve.py -p rabbitmq-operator -t recreate -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```                                    
[ERROR] statefulset/default/rabbitmq-cluster-server DELETE inconsistency: 1 events seen during normal run, but 2 seen during testing run 
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

### [rabbitmq-cluster-operator-653](https://github.com/rabbitmq/cluster-operator/issues/653)
```
python3 sieve.py -p rabbitmq-operator -t resize-pvc -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] statefulset/default/rabbitmq-cluster-server DELETE inconsistency: 1 events seen during learning run, but 3 seen during testing run
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

### [K8SPSMDB-430](https://jira.percona.com/browse/K8SPSMDB-430)
```
python3 sieve.py -p mongodb-operator -t recreate -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim/default/mongod-data-mongodb-cluster-rs0-2 DELETE inconsistency: 1 events seen during learning run, but 10 seen during testing run
[ERROR] pod SIZE inconsistency: 4 seen after learning run, but 3 seen after testing run
[ERROR] persistentvolumeclaim SIZE inconsistency: 3 seen after learning run, but 2 seen after testing run
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

### [K8SPSMDB-433](https://jira.percona.com/browse/K8SPSMDB-433)
```
python3 sieve.py -p mongodb-operator -t disable-enable-shard -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] statefulset/default/mongodb-cluster-cfg DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

### [K8SPSMDB-438](https://jira.percona.com/browse/K8SPSMDB-438)
```
python3 sieve.py -p mongodb-operator -t disable-enable-arbiter -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] statefulset/default/mongodb-cluster-rs0-arbiter DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

### [K8SPXC-716](https://jira.percona.com/browse/K8SPXC-716)
```
python3 sieve.py -p xtradb-operator -t recreate -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim/default/datadir-xtradb-cluster-pxc-2 DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

### [K8SPXC-725](https://jira.percona.com/browse/K8SPXC-725)
```
python3 sieve.py -p xtradb-operator -t disable-enable-haproxy -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] statefulset/default/xtradb-cluster-haproxy DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

### [K8SPXC-763](https://jira.percona.com/browse/K8SPXC-763)
```
python3 sieve.py -p xtradb-operator -t disable-enable-proxysql -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] statefulset/default/xtradb-cluster-proxysql DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

<!-- ### [datastax-cass-operator-412](https://github.com/datastax/cass-operator/issues/412) -->
### [k8ssandra-cass-operator (originally datastax-cass-operator-412)](https://github.com/k8ssandra/cass-operator/issues/118)
First build the images if you have not yet (`DOCKER_REPO_NAME` should be the docker repo that you have write access to)
```
python3 build.py -p kubernetes -m time-travel -d DOCKER_REPO_NAME
python3 build.py -p cass-operator -m time-travel -d DOCKER_REPO_NAME
```
Then run the sieve test
```
python3 sieve.py -p cass-operator -t recreate -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim TERMINATING inconsistency: 0 seen after learning run, but 1 seen after testing run
[ERROR] persistentvolumeclaim/default/server-data-cluster1-cassandra-datacenter-default-sts-0 DELETE inconsistency: 1 events seen during learning run, but 13 seen during testing run
```
The bug was found in commit `dbd4f7a10533bb2298aed0d40ea20bfd8c133da2`.

### [orange-opensource-casskop-316](https://github.com/Orange-OpenSource/casskop/issues/316)
```
python3 sieve.py -p casskop-operator -t recreate -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim TERMINATING inconsistency: 0 seen after learning run, but 1 seen after testing run
[ERROR] persistentvolumeclaim/default/data-cassandra-cluster-dc1-rack1-0 DELETE inconsistency: 1 events seen during learning run, but 13 seen during testing run
```
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.

### [orange-opensource-casskop-321](https://github.com/Orange-OpenSource/casskop/issues/321)
```
python3 sieve.py -p casskop-operator -t reducepdb -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] poddisruptionbudget/default/cassandra-cluster DELETE inconsistency: 1 events seen during learning run, but 3 seen during testing run
```
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.

### [yugabyte/yugabyte-operator-35](https://github.com/yugabyte/yugabyte-operator/issues/35)
```
python3 sieve.py -p yugabyte-operator -t disable-enable-tls -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] secret/default/yb-tserver-yugabyte-tls-cert DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
This bug was found in commit `966ef1978ed5d714119548b2c4343925fe49f882`.

### [yugabyte/yugabyte-operator-36](https://github.com/yugabyte/yugabyte-operator/issues/36)
```
python3 sieve.py -p yugabyte-operator -t disable-enable-tls -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] service/default/yb-tserver-ui DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
This bug was found in commit `966ef1978ed5d714119548b2c4343925fe49f882` with the prerequisite 
[fix](https://github.com/yugabyte/yugabyte-operator/pull/34).

### Observability gaps
First, build the operators:
```
python3 build.py -p kubernetes -m obs-gap -d DOCKER_REPO_NAME
python3 build.py -p cassandra-operator -m obs-gap -d DOCKER_REPO_NAME
python3 build.py -p rabbitmq-operator -m obs-gap -d DOCKER_REPO_NAME
python3 build.py -p casskop-operator -m obs-gap -d DOCKER_REPO_NAME
```
Please specify the `DOCKER_REPO_NAME` that you have write access to as sieve needs to push controller image to the repo.

The above commands will download, instrument and build Kubernetes and controller images used for testing.
For Kubernetes, we use the branch `v1.18.9`.
For each controller, we use a default commit SHA specified in `controllers.py`. You can also specify which commit of the operator you want to test by `-s COMMIT_SHA`, but the bugs may not be reproduced with other commits as some of them have been fixed after our reports.

### [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398)
```
python3 sieve.py -p cassandra-operator -t scaledown -d DOCKER_REPO_NAME
```
If reproduced, you will find
```
[ERROR] persistentvolumeclaim SIZE inconsistency: 1 seen after learning run, but 2 seen after testing run
```
The bug was found in commit `fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd`.

### [instaclustr-cassandra-operator-410](https://github.com/instaclustr/cassandra-operator/issues/410)
to do (we need to improve the oracle)

### [rabbitmq-cluster-operator-758](https://github.com/rabbitmq/cluster-operator/issues/758)
```
python3 sieve.py -p rabbitmq-operator -t scaleup-scaledown -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim SIZE inconsistency: 3 seen after learning run, but 2 seen after testing run
[ERROR] pod SIZE inconsistency: 4 seen after learning run, but 3 seen after testing run
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

### [orange-opensource-casskop-342](https://github.com/Orange-OpenSource/casskop/issues/342)
```
python3 sieve.py -p casskop-operator -t scaledown-to-zero -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim SIZE inconsistency: 1 seen after learning run, but 2 seen after testing run
[ERROR] pod SIZE inconsistency: 2 seen after learning run, but 3 seen after testing run
```
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.

### [orange-opensource-casskop-357](https://github.com/Orange-OpenSource/casskop/issues/357)
```
python3 sieve.py -p casskop-operator -t scaledown-obs-gap -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[RESOURCE DIFF]
[spec field changed] cassandracluster sonar-cassandra-cluster topology changed delta:  {'dc': {insert: [(0, {'name': 'SIEVE-IGNORE', 'nodesPerRacks': 1, 'rack': [{'name': 'SIEVE-IGNORE'}], 'resources': {}}), (1, {'name': 'SIEVE-IGNORE', 'nodesPerRacks': 1, 'rack': [{'name': 'SIEVE-IGNORE'}], 'resources': {}})]}}
[status field changed] cassandracluster sonar-cassandra-cluster cassandraRackStatus changed delta:  {insert: {'dc2-rack1': {'cassandraLastAction': {'name': 'SIEVE-IGNORE', 'status': 'Ongoing'}, 'phase': 'Initializing', 'podLastOperation': {}}, 'dc3-rack1': {'cassandraLastAction': {'name': 'SIEVE-IGNORE', 'status': 'Ongoing'}, 'phase': 'Initializing', 'podLastOperation': {}}}}
```
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.

### [K8SPSMDB-434](https://jira.percona.com/browse/K8SPSMDB-434)
to be updated

### Broken atomicity

### [rabbitmq-cluster-operator-782](https://github.com/rabbitmq/cluster-operator/issues/782)
```
python3 sieve.py -p rabbitmq-operator -t resize-pvc-atomic -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[RESOURCE DIFF]
values_changed persistentvolumeclaim default persistence-rabbitmq-cluster-server-0 spec/resources/requests/storage 15Gi  =>  10Gi
values_changed persistentvolumeclaim default persistence-rabbitmq-cluster-server-0 status/capacity/storage 15Gi  =>  10Gi
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

## [orange-opensource-nifikop-130](https://github.com/Orange-OpenSource/nifikop/issues/130)
```
python3 sieve.py -p nifikop-operator -t change-config -d DOCKER_REPO_NAME
```
If reproduced, you will see:
```
[ERROR] pod/default/simplenifi-1.* CREATE inconsistency: 2 events seen during learning run, but 1 seen during testing run
[ERROR] pod/default/simplenifi-1.* DELETE inconsistency: 1 events seen during learning run, but 0 seen during testing run
```
The bug was found in commit `1546e0242107bf2f2c1256db50f47c79956dd1c6`.
