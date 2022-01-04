## Bug Reproduction

**Before reproducing the bugs**, please ensure your local environment meets all the [requirements](https://github.com/sieve-project/sieve#requirements) otherwise Sieve may not work, and set `docker_repo` in your `sieve_config.json` to `ghcr.io/sieve-project/action` (the default value).


### Atomicity violation

### [k8ssandra-cass-operator-1023](https://k8ssandra.atlassian.net/browse/K8SSAND-1023)
```
python3 reprod.py -p cass-operator -b atom-vio-1
```
If reproduced, you will see:
```
[ALARM][WORKLOAD] error: hard timeout: cluster1-cassandra-datacenter-default-sts-0 does not become Running within 600 seconds                     
[ALARM][WORKLOAD] error: hard timeout: cluster1-cassandra-datacenter-default-sts-0 does not become Running within 600 seconds
...
```
The bug was found in commit `dbd4f7a10533bb2298aed0d40ea20bfd8c133da2`.

### [orange-opensource-casskop-370](https://github.com/Orange-OpenSource/casskop/issues/370)
```
python3 reprod.py -p casskop-operator -b atom-vio-1
```
If reproduced, you will see:
```
[ALARM][EVENT][KEY] /persistentvolumeclaims/default/data-cassandra-cluster-dc1-rack1-1 DELETED inconsistency: 1 events seen during learning run, but 0 seen during testing run
[ALARM][ALARM][RESOURCE-ADD] persistentvolumeclaim/data-cassandra-cluster-dc1-rack1-1 is not seen during learning run, but seen during testing run
```
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.


### [orange-opensource-nifikop-130](https://github.com/Orange-OpenSource/nifikop/issues/130)
```
python3 reprod.py -p nifikop-operator -b atom-vio-1
```
If reproduced, you will see:
```
[ALARM][EVENT][KEY] /pods/default/simplenifi-1-node* ADDED inconsistency: 2 events seen during learning run, but 1 seen during testing run
[ALARM][EVENT][KEY] /pods/default/simplenifi-1-node* DELETED inconsistency: 1 events seen during learning run, but 0 seen during testing run
```
The bug was found in commit `1546e0242107bf2f2c1256db50f47c79956dd1c6`.

### [rabbitmq-cluster-operator-782](https://github.com/rabbitmq/cluster-operator/issues/782)
```
python3 reprod.py -p rabbitmq-operator -b atom-vio-1
```
If reproduced, you will see:
```
[ALARM][RESOURCE-KEY-DIFF] persistentvolumeclaim/default/persistence-rabbitmq-cluster-server-0 spec/resources/requests/storage is 15Gi during learning run, but 10Gi during testing run
[ALARM][RESOURCE-KEY-DIFF] persistentvolumeclaim/default/persistence-rabbitmq-cluster-server-0 status/capacity/storage is 15Gi during learning run, but 10Gi during testing run
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

### [rabbitmq-cluster-operator-782](https://github.com/rabbitmq/cluster-operator/issues/782)
```
python3 reprod.py -p rabbitmq-operator -b atom-vio-1
```
If reproduced, you will see:
```
[ALARM][RESOURCE-KEY-DIFF] persistentvolumeclaim/default/persistence-rabbitmq-cluster-server-0 spec/resources/requests/storage is 15Gi during learning run, but 10Gi during testing run
[ALARM][RESOURCE-KEY-DIFF] persistentvolumeclaim/default/persistence-rabbitmq-cluster-server-0 status/capacity/storage is 15Gi during learning run, but 10Gi during testing run
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

### [percona-server-mongodb-operator-578](https://jira.percona.com/browse/K8SPSMDB-578)
```
python3 reprod.py -p mongodb-operator -b atom-vio-1
```
If reproduced, you will see:
```
[ALARM][ALARM][RESOURCE-REMOVE] 8 secret seen after learning run ['default-token-v5xjx', 'internal-mongodb-cluster-users', 'mongodb-cluster-mongodb-encryption-key', 'mongodb-cluster-mongodb-keyfile', 'mongodb-cluster-secrets', 'mongodb-cluster-ssl', 'mongodb-cluster-ssl-internal', 'percona-server-mongodb-operator-token-ntftn'] but 7 secret seen after testing run ['default-token-2ftjd', 'internal-mongodb-cluster-users', 'mongodb-cluster-mongodb-encryption-key', 'mongodb-cluster-mongodb-keyfile', 'mongodb-cluster-secrets', 'mongodb-cluster-ssl', 'percona-server-mongodb-operator-token-tgg6p']
...
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

### [percona-server-mongodb-operator-579](https://jira.percona.com/browse/K8SPSMDB-579)
```
python3 reprod.py -p mongodb-operator -b atom-vio-2
```
If reproduced, you will see:
```
[ALARM][ALARM][RESOURCE-REMOVE] 8 secret seen after learning run ['default-token-wk4d2', 'internal-mongodb-cluster-users', 'mongodb-cluster-mongodb-encryption-key', 'mongodb-cluster-mongodb-keyfile', 'mongodb-cluster-secrets', 'mongodb-cluster-ssl', 'mongodb-cluster-ssl-internal', 'percona-server-mongodb-operator-token-8gj55'] but 7 secret seen after testing run ['default-token-9fzlj', 'internal-mongodb-cluster-users', 'mongodb-cluster-mongodb-encryption-key', 'mongodb-cluster-mongodb-keyfile', 'mongodb-cluster-secrets', 'mongodb-cluster-ssl', 'percona-server-mongodb-operator-token-qb5xx']
[ALARM][ALARM][RESOURCE-REMOVE] certificate/mongodb-cluster-ssl-internal is seen during learning run, but not seen during testing run
...
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

### [percona-xtradb-cluster-operator-896](https://jira.percona.com/browse/K8SPXC-896)
```
python3 reprod.py -p xtradb-operator -b atom-vio-1
```
If reproduced, you will see:
```
[ALARM][ALARM][RESOURCE-REMOVE] 6 secret seen after learning run ['default-token-nnl9s', 'internal-xtradb-cluster', 'percona-xtradb-cluster-operator-token-z9v9v', 'xtradb-cluster-secrets', 'xtradb-cluster-ssl', 'xtradb-cluster-ssl-internal'] but 5 secret seen after testing run ['default-token-v2vpv', 'internal-xtradb-cluster', 'percona-xtradb-cluster-operator-token-mkmlg', 'xtradb-cluster-secrets', 'xtradb-cluster-ssl']
...
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

### [percona-xtradb-cluster-operator-897](https://jira.percona.com/browse/K8SPXC-897)
```
python3 reprod.py -p xtradb-operator -b atom-vio-2
```
If reproduced, you will see:
```
[ALARM][ALARM][RESOURCE-REMOVE] 6 secret seen after learning run ['default-token-sx9c2', 'internal-xtradb-cluster', 'percona-xtradb-cluster-operator-token-fl84z', 'xtradb-cluster-secrets', 'xtradb-cluster-ssl', 'xtradb-cluster-ssl-internal'] but 5 secret seen after testing run ['default-token-llvtq', 'internal-xtradb-cluster', 'percona-xtradb-cluster-operator-token-bwpzc', 'xtradb-cluster-secrets', 'xtradb-cluster-ssl']
[ALARM][ALARM][RESOURCE-REMOVE] certificate/xtradb-cluster-ssl-internal is seen during learning run, but not seen during testing run
[ALARM][ALARM][RESOURCE-REMOVE] certificaterequest/xtradb-cluster-ssl-internal-4197621709 is seen during learning run, but not seen during testing run
...
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

### Observability gaps

### [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398)
```
python3 reprod.py -p cassandra-operator -b obs-gap-1
```
If reproduced, you will find
```
[ERROR] persistentvolumeclaim SIZE inconsistency: 1 seen after learning run, but 2 seen after testing run
```
The bug was found in commit `fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd`.

### [rabbitmq-cluster-operator-758](https://github.com/rabbitmq/cluster-operator/issues/758)
```
python3 reprod.py -p rabbitmq-operator -b obs-gap-1
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim SIZE inconsistency: 3 seen after learning run, but 2 seen after testing run
[ERROR] pod SIZE inconsistency: 4 seen after learning run, but 3 seen after testing run
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

### [orange-opensource-casskop-342](https://github.com/Orange-OpenSource/casskop/issues/342)
```
python3 reprod.py -p casskop-operator -b obs-gap-1
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim SIZE inconsistency: 1 seen after learning run, but 2 seen after testing run
[ERROR] pod SIZE inconsistency: 2 seen after learning run, but 3 seen after testing run
```
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.


### [yugabyte-operator-39](https://github.com/yugabyte/yugabyte-operator/issues/39)
```
python3 reprod.py -p yugabyte-operator -b obs-gap-1
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
python3 reprod.py -p cassandra-operator -b time-travel-1
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
python3 reprod.py -p cassandra-operator -b time-travel-2
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim TERMINATING inconsistency: 0 seen after learning run, but 1 seen after testing run
[ERROR] persistentvolumeclaim/default/data-volume-cassandra-test-cluster-dc1-rack1-1 DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `bd8077a478997f63862848d66d4912c59e4c46ff`.

### [pravega-zookeeper-operator-312](https://github.com/pravega/zookeeper-operator/issues/312)
```
python3 reprod.py -p zookeeper-operator -b time-travel-1
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
python3 reprod.py -p zookeeper-operator -b time-travel-2
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim/default/data-zookeeper-cluster-1 DELETE inconsistency: 1 events seen during learning run, but 7 seen during testing run
```
The bug was found in commit `cda03d2f270bdfb51372192766123904f6d88278`.

### [rabbitmq-cluster-operator-648](https://github.com/rabbitmq/cluster-operator/issues/648)
```
python3 reprod.py -p rabbitmq-operator -b time-travel-1
```
If reproduced, you will see:
```                                    
[ERROR] statefulset/default/rabbitmq-cluster-server DELETE inconsistency: 1 events seen during normal run, but 2 seen during testing run 
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

### [rabbitmq-cluster-operator-653](https://github.com/rabbitmq/cluster-operator/issues/653)
```
python3 reprod.py -p rabbitmq-operator -b time-travel-2
```
If reproduced, you will see:
```
[ERROR] statefulset/default/rabbitmq-cluster-server DELETE inconsistency: 1 events seen during learning run, but 3 seen during testing run
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

### [K8SPSMDB-430](https://jira.percona.com/browse/K8SPSMDB-430)
```
python3 reprod.py -p mongodb-operator -b time-travel-1
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim/default/mongod-data-mongodb-cluster-rs0-2 DELETE inconsistency: 1 events seen during learning run, but 11 seen during testing run
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

### [K8SPSMDB-433](https://jira.percona.com/browse/K8SPSMDB-433)
```
python3 reprod.py -p mongodb-operator -b time-travel-2
```
If reproduced, you will see:
```
[ERROR] statefulset/default/mongodb-cluster-cfg DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

### [K8SPSMDB-438](https://jira.percona.com/browse/K8SPSMDB-438)
```
python3 reprod.py -p mongodb-operator -b time-travel-3
```
If reproduced, you will see:
```
[ERROR] statefulset/default/mongodb-cluster-rs0-arbiter DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

### [K8SPXC-716](https://jira.percona.com/browse/K8SPXC-716)
```
python3 reprod.py -p xtradb-operator -b time-travel-1
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim/default/datadir-xtradb-cluster-pxc-2 DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

### [K8SPXC-725](https://jira.percona.com/browse/K8SPXC-725)
```
python3 reprod.py -p xtradb-operator -b time-travel-2
```
If reproduced, you will see:
```
[ERROR] statefulset/default/xtradb-cluster-haproxy DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

### [K8SPXC-763](https://jira.percona.com/browse/K8SPXC-763)
```
python3 reprod.py -p xtradb-operator -b time-travel-3
```
If reproduced, you will see:
```
[ERROR] statefulset/default/xtradb-cluster-proxysql DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

<!-- ### [datastax-cass-operator-412](https://github.com/datastax/cass-operator/issues/412) -->
### [k8ssandra-cass-operator (originally datastax-cass-operator-412)](https://github.com/k8ssandra/cass-operator/issues/118)
```
python3 reprod.py -p cass-operator -b time-travel-1
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim TERMINATING inconsistency: 0 seen after learning run, but 1 seen after testing run
[ERROR] persistentvolumeclaim/default/server-data-cluster1-cassandra-datacenter-default-sts-0 DELETE inconsistency: 1 events seen during learning run, but 13 seen during testing run
```
The bug was found in commit `dbd4f7a10533bb2298aed0d40ea20bfd8c133da2`.

### [orange-opensource-casskop-316](https://github.com/Orange-OpenSource/casskop/issues/316)
```
python3 reprod.py -p casskop-operator -b time-travel-1
```
If reproduced, you will see:
```
[ERROR] persistentvolumeclaim TERMINATING inconsistency: 0 seen after learning run, but 1 seen after testing run
[ERROR] persistentvolumeclaim/default/data-cassandra-cluster-dc1-rack1-0 DELETE inconsistency: 1 events seen during learning run, but 13 seen during testing run
```
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.

### [orange-opensource-casskop-321](https://github.com/Orange-OpenSource/casskop/issues/321)
```
python3 reprod.py -p casskop-operator -b time-travel-2
```
If reproduced, you will see:
```
[ERROR] poddisruptionbudget/default/cassandra-cluster DELETE inconsistency: 1 events seen during learning run, but 3 seen during testing run
```
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.

### [yugabyte/yugabyte-operator-35](https://github.com/yugabyte/yugabyte-operator/issues/35)
```
python3 reprod.py -p yugabyte-operator -b time-travel-1
```
If reproduced, you will see:
```
[ERROR] secret/default/yb-tserver-yugabyte-tls-cert DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
This bug was found in commit `966ef1978ed5d714119548b2c4343925fe49f882`.

### [yugabyte/yugabyte-operator-36](https://github.com/yugabyte/yugabyte-operator/issues/36)
```
python3 reprod.py -p yugabyte-operator -b time-travel-2
```
If reproduced, you will see:
```
[ERROR] service/default/yb-tserver-ui DELETE inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
This bug was found in commit `966ef1978ed5d714119548b2c4343925fe49f882` with the prerequisite 
[fix](https://github.com/yugabyte/yugabyte-operator/pull/34).

