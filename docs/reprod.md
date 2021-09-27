## Bug Reproduction

**Before reproducing the bugs, please ensure your local environment meets all the [requirements](https://github.com/sieve-project/sieve#requirements) otherwise Sieve may not work.**

**Before reproducing the bugs, please first set**
```
export SIEVE_IMAGE="ghcr.io/sieve-project/action"
```

### Atomicity violation

### [rabbitmq-cluster-operator-782](https://github.com/rabbitmq/cluster-operator/issues/782)
```
python3 reprod.py -p rabbitmq-operator -b atom-vio-1 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[RESOURCE DIFF]
values_changed persistentvolumeclaim default persistence-rabbitmq-cluster-server-0 spec/resources/requests/storage 15Gi  =>  10Gi
values_changed persistentvolumeclaim default persistence-rabbitmq-cluster-server-0 status/capacity/storage 15Gi  =>  10Gi
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

### [orange-opensource-nifikop-130](https://github.com/Orange-OpenSource/nifikop/issues/130)
```
python3 reprod.py -p nifikop-operator -b atom-vio-1 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] pod/default/simplenifi-1.* CREATE inconsistency: 2 events seen during learning run, but 1 seen during testing run
[ERROR] pod/default/simplenifi-1.* DELETE inconsistency: 1 events seen during learning run, but 0 seen during testing run
```
The bug was found in commit `1546e0242107bf2f2c1256db50f47c79956dd1c6`.

### Observability gaps

### [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398)
```
python3 reprod.py -p cassandra-operator -b obs-gap-1 -d SIEVE_IMAGE
```
If reproduced, you will find
```
[ERROR] persistentvolumeclaim SIZE inconsistency: 1 seen after learning run, but 2 seen after testing run
```
The bug was found in commit `fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd`.

### [rabbitmq-cluster-operator-758](https://github.com/rabbitmq/cluster-operator/issues/758)
```
python3 reprod.py -p rabbitmq-operator -b obs-gap-1 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim SIZE inconsistency: 3 seen after learning run, but 2 seen after testing run
[ERROR] pod SIZE inconsistency: 4 seen after learning run, but 3 seen after testing run
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

### [orange-opensource-casskop-342](https://github.com/Orange-OpenSource/casskop/issues/342)
```
python3 reprod.py -p casskop-operator -b obs-gap-1 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim SIZE inconsistency: 1 seen after learning run, but 2 seen after testing run
[ERROR] pod SIZE inconsistency: 2 seen after learning run, but 3 seen after testing run
```
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.

<!-- ### [orange-opensource-casskop-357](https://github.com/Orange-OpenSource/casskop/issues/357)
todo -->
<!-- ```
python3 reprod.py -p casskop-operator -b obs-gap-2 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[RESOURCE DIFF]
[spec field changed] cassandracluster sonar-cassandra-cluster topology changed delta:  {'dc': {insert: [(0, {'name': 'SIEVE-IGNORE', 'nodesPerRacks': 1, 'rack': [{'name': 'SIEVE-IGNORE'}], 'resources': {}}), (1, {'name': 'SIEVE-IGNORE', 'nodesPerRacks': 1, 'rack': [{'name': 'SIEVE-IGNORE'}], 'resources': {}})]}}
[status field changed] cassandracluster sonar-cassandra-cluster cassandraRackStatus changed delta:  {insert: {'dc2-rack1': {'cassandraLastAction': {'name': 'SIEVE-IGNORE', 'status': 'Ongoing'}, 'phase': 'Initializing', 'podLastOperation': {}}, 'dc3-rack1': {'cassandraLastAction': {'name': 'SIEVE-IGNORE', 'status': 'Ongoing'}, 'phase': 'Initializing', 'podLastOperation': {}}}}
```
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`. -->

### [yugabyte/yugabyte-operator-39](https://github.com/yugabyte/yugabyte-operator/issues/39)
```
python3 reprod.py -p yugabyte-operator -b obs-gap-1 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] pod SIZE inconsistency: 8 seen after learning run, but 7 seen after testing run
[ERROR] persistentvolumeclaim SIZE inconsistency: 7 seen after learning run, but 6 seen after testing run
```
This bug was found in commit `966ef1978ed5d714119548b2c4343925fe49f882`.

### Time travel

### [instaclustr-cassandra-operator-402](https://github.com/instaclustr/cassandra-operator/issues/402)
```
python3 reprod.py -p cassandra-operator -b time-travel-1 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim/default/data-volume-cassandra-test-cluster-dc1-rack1-0 DELETE inconsistency: 1 events seen during learning run, but 13 seen during testing run
Checking for cluster resource states...
[ERROR] persistentvolumeclaim TERMINATING inconsistency: 0 seen after learning run, but 1 seen after testing run
```
The bug was found in commit `fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd`.

### [instaclustr-cassandra-operator-407](https://github.com/instaclustr/cassandra-operator/issues/407)
```
python3 reprod.py -p cassandra-operator -b time-travel-2 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim TERMINATING inconsistency: 0 seen after learning run, but 1 seen after testing run
[ERROR] persistentvolumeclaim/default/data-volume-cassandra-test-cluster-dc1-rack1-1 DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `bd8077a478997f63862848d66d4912c59e4c46ff`.

### [pravega-zookeeper-operator-312](https://github.com/pravega/zookeeper-operator/issues/312)
```
python3 reprod.py -p zookeeper-operator -b time-travel-1 -d SIEVE_IMAGE
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
python3 reprod.py -p zookeeper-operator -b time-travel-2 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim/default/data-zookeeper-cluster-1 DELETE inconsistency: 1 events seen during learning run, but 7 seen during testing run
```
The bug was found in commit `cda03d2f270bdfb51372192766123904f6d88278`.

### [rabbitmq-cluster-operator-648](https://github.com/rabbitmq/cluster-operator/issues/648)
```
python3 reprod.py -p rabbitmq-operator -b time-travel-1 -d SIEVE_IMAGE
```
If reproduced, you will see:
```                                    
[ERROR] statefulset/default/rabbitmq-cluster-server DELETE inconsistency: 1 events seen during normal run, but 2 seen during testing run 
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

### [rabbitmq-cluster-operator-653](https://github.com/rabbitmq/cluster-operator/issues/653)
```
python3 reprod.py -p rabbitmq-operator -b time-travel-2 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] statefulset/default/rabbitmq-cluster-server DELETE inconsistency: 1 events seen during learning run, but 3 seen during testing run
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

### [K8SPSMDB-430](https://jira.percona.com/browse/K8SPSMDB-430)
```
python3 reprod.py -p mongodb-operator -b time-travel-1 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim/default/mongod-data-mongodb-cluster-rs0-2 DELETE inconsistency: 1 events seen during learning run, but 11 seen during testing run
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

### [K8SPSMDB-433](https://jira.percona.com/browse/K8SPSMDB-433)
```
python3 reprod.py -p mongodb-operator -b time-travel-2 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] statefulset/default/mongodb-cluster-cfg DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

### [K8SPSMDB-438](https://jira.percona.com/browse/K8SPSMDB-438)
```
python3 reprod.py -p mongodb-operator -b time-travel-3 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] statefulset/default/mongodb-cluster-rs0-arbiter DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

### [K8SPXC-716](https://jira.percona.com/browse/K8SPXC-716)
```
python3 reprod.py -p xtradb-operator -b time-travel-1 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim/default/datadir-xtradb-cluster-pxc-2 DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

### [K8SPXC-725](https://jira.percona.com/browse/K8SPXC-725)
```
python3 reprod.py -p xtradb-operator -b time-travel-2 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] statefulset/default/xtradb-cluster-haproxy DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

### [K8SPXC-763](https://jira.percona.com/browse/K8SPXC-763)
```
python3 reprod.py -p xtradb-operator -b time-travel-3 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] statefulset/default/xtradb-cluster-proxysql DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

<!-- ### [datastax-cass-operator-412](https://github.com/datastax/cass-operator/issues/412) -->
### [k8ssandra-cass-operator (originally datastax-cass-operator-412)](https://github.com/k8ssandra/cass-operator/issues/118)
```
python3 reprod.py -p cass-operator -b time-travel-1 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim TERMINATING inconsistency: 0 seen after learning run, but 1 seen after testing run
[ERROR] persistentvolumeclaim/default/server-data-cluster1-cassandra-datacenter-default-sts-0 DELETE inconsistency: 1 events seen during learning run, but 13 seen during testing run
```
The bug was found in commit `dbd4f7a10533bb2298aed0d40ea20bfd8c133da2`.

### [orange-opensource-casskop-316](https://github.com/Orange-OpenSource/casskop/issues/316)
```
python3 reprod.py -p casskop-operator -b time-travel-1 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim TERMINATING inconsistency: 0 seen after learning run, but 1 seen after testing run
[ERROR] persistentvolumeclaim/default/data-cassandra-cluster-dc1-rack1-0 DELETE inconsistency: 1 events seen during learning run, but 13 seen during testing run
```
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.

### [orange-opensource-casskop-321](https://github.com/Orange-OpenSource/casskop/issues/321)
```
python3 reprod.py -p casskop-operator -b time-travel-2 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] poddisruptionbudget/default/cassandra-cluster DELETE inconsistency: 1 events seen during learning run, but 3 seen during testing run
```
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.

### [yugabyte/yugabyte-operator-35](https://github.com/yugabyte/yugabyte-operator/issues/35)
```
python3 reprod.py -p yugabyte-operator -b time-travel-1 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] secret/default/yb-tserver-yugabyte-tls-cert DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
This bug was found in commit `966ef1978ed5d714119548b2c4343925fe49f882`.

### [yugabyte/yugabyte-operator-36](https://github.com/yugabyte/yugabyte-operator/issues/36)
```
python3 reprod.py -p yugabyte-operator -b time-travel-2 -d SIEVE_IMAGE
```
If reproduced, you will see:
```
[ERROR] service/default/yb-tserver-ui DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
This bug was found in commit `966ef1978ed5d714119548b2c4343925fe49f882` with the prerequisite 
[fix](https://github.com/yugabyte/yugabyte-operator/pull/34).

