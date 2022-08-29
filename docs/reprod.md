# Bug Reproduction

**Before reproducing the bugs**, please ensure your local environment meets all the [requirements](https://github.com/sieve-project/sieve#requirements) otherwise Sieve may not work, and set `docker_repo` in your `sieve_config.json` to `ghcr.io/sieve-project/action` (the default value).

## 31 intermediate-, stale-, and unobservable-state bugs
Sieve can consistently reproduce all the 31 intermediate-, stale-, and unobservable-state bugs.

### [cass-operator](https://github.com/k8ssandra/cass-operator)

#### intermediate-state bug 1: [k8ssandra-cass-operator-1023](https://k8ssandra.atlassian.net/browse/K8SSAND-1023)
```
python3 reproduce_bugs.py -c cass-operator -b intermediate-state-1
```
If reproduced, you will see errors reported by Sieve including
```
Error from the workload: error: hard timeout: cluster1-cassandra-datacenter-default-sts-0 does not become Running within 1000 seconds
```
The bug was found in commit `dbd4f7a10533bb2298aed0d40ea20bfd8c133da2`.

<!-- #### [datastax-cass-operator-412](https://github.com/datastax/cass-operator/issues/412) -->
#### stale-state bug 1: [k8ssandra-cass-operator-559](https://k8ssandra.atlassian.net/browse/K8SSAND-559)
```
python3 reproduce_bugs.py -c cass-operator -b stale-state-1
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - more object fields than reference: persistentvolumeclaim/default/server-data-cluster1-cassandra-datacenter-default-sts-0["metadata"]["deletionTimestamp"] not seen after reference run, but is 2022-04-01T05:31:17Z after testing run
```
Note that the timestamp can change.
The bug was found in commit `dbd4f7a10533bb2298aed0d40ea20bfd8c133da2`.

### [cassandra-operator](https://github.com/instaclustr/cassandra-operator)

#### stale-state bug 1: [instaclustr-cassandra-operator-402](https://github.com/instaclustr/cassandra-operator/issues/402)
```
python3 reproduce_bugs.py -c cassandra-operator -b stale-state-1
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - more object fields than reference: persistentvolumeclaim/default/data-volume-cassandra-test-cluster-dc1-rack1-0["metadata"]["deletionTimestamp"] not seen after reference run, but is 2022-04-01T04:22:06Z after testing run
```
Note that the timestamp can change.
The bug was found in commit `fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd`.

#### stale-state bug 2: [instaclustr-cassandra-operator-407](https://github.com/instaclustr/cassandra-operator/issues/407)
```
python3 reproduce_bugs.py -c cassandra-operator -b stale-state-2
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - more object fields than reference: persistentvolumeclaim/default/data-volume-cassandra-test-cluster-dc1-rack1-1["metadata"]["deletionTimestamp"] not seen after reference run, but is 2022-04-01T04:34:00Z after testing run
```
Note that the timestamp can change.
The bug was found in commit `fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd`.

#### unobserved-state bug 1: [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398)
```
python3 reproduce_bugs.py -c cassandra-operator -b unobserved-state-1
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - object field has a different value: pod/default/cassandra-test-cluster-dc1-rack1-1["status"]["containerStatuses"][0]["ready"] is True after reference run, but False after testing run
```
The bug was found in commit `fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd`.

### [casskop](https://github.com/Orange-OpenSource/casskop)

#### intermediate-state bug 1: [orange-opensource-casskop-370](https://github.com/Orange-OpenSource/casskop/issues/370)
```
python3 reproduce_bugs.py -c casskop-operator -b intermediate-state-1
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - more objects than reference: persistentvolumeclaim/default/data-cassandra-cluster-dc1-rack1-1 is not seen after reference run, but seen after testing run
End state inconsistency - object field has a different value: cassandracluster/default/cassandra-cluster["status"]["cassandraRackStatus"]["dc1-rack1"]["cassandraLastAction"]["status"] is Done after reference run, but ToDo after testing run
```
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.

#### stale-state bug 1: [orange-opensource-casskop-316](https://github.com/Orange-OpenSource/casskop/issues/316)
```
python3 reproduce_bugs.py -c casskop-operator -b stale-state-1
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - more object fields than reference: persistentvolumeclaim/default/data-cassandra-cluster-dc1-rack1-0["metadata"]["deletionTimestamp"] not seen after reference run, but is 2022-04-01T05:46:44Z after testing run
```
Note that the timestamp can change.
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.

#### stale-state bug 2: [orange-opensource-casskop-321](https://github.com/Orange-OpenSource/casskop/issues/321)
```
python3 reproduce_bugs.py -c casskop-operator -b stale-state-2
```
If reproduced, you will see errors reported by Sieve including
```
State-update summaries inconsistency: poddisruptionbudget/default/cassandra-cluster ADDED inconsistency: 2 event(s) seen during reference run, but 4 seen during testing run
State-update summaries inconsistency: poddisruptionbudget/default/cassandra-cluster DELETED inconsistency: 1 event(s) seen during reference run, but 3 seen during testing run
```
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.

#### unobserved-state bug 1: [orange-opensource-casskop-342](https://github.com/Orange-OpenSource/casskop/issues/342)
```
python3 reproduce_bugs.py -c casskop-operator -b unobserved-state-1
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - more objects than reference: 2 pod object(s) seen after reference run ['pod/default/cassandra-cluster-dc1-rack1-0', 'pod/default/casskop-operator-546674cfdd-z486x'] but 3 pod object(s) seen after testing run ['pod/default/cassandra-cluster-dc1-rack1-0', 'pod/default/cassandra-cluster-dc1-rack1-1', 'pod/default/casskop-operator-67fdccf6f4-s6cgt']
```
Note that the randomly generated pod name can change.
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.

### [mongodb-operator](https://github.com/percona/percona-server-mongodb-operator)

#### intermediate-state bug 1: [percona-server-mongodb-operator-578](https://jira.percona.com/browse/K8SPSMDB-578)
```
python3 reproduce_bugs.py -c mongodb-operator -b intermediate-state-1
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - fewer objects than reference: 7 secret object(s) seen after reference run ['secret/default/internal-mongodb-cluster-users', 'secret/default/mongodb-cluster-mongodb-encryption-key', 'secret/default/mongodb-cluster-mongodb-keyfile', 'secret/default/mongodb-cluster-secrets', 'secret/default/mongodb-cluster-ssl', 'secret/default/mongodb-cluster-ssl-internal', 'secret/default/percona-server-mongodb-operator-token-4pbxq'] but 6 secret object(s) seen after testing run ['secret/default/internal-mongodb-cluster-users', 'secret/default/mongodb-cluster-mongodb-encryption-key', 'secret/default/mongodb-cluster-mongodb-keyfile', 'secret/default/mongodb-cluster-secrets', 'secret/default/mongodb-cluster-ssl', 'secret/default/percona-server-mongodb-operator-token-rkglb']
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

#### intermediate-state bug 2: [percona-server-mongodb-operator-579](https://jira.percona.com/browse/K8SPSMDB-579)
```
python3 reproduce_bugs.py -c mongodb-operator -b intermediate-state-2
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - fewer objects than reference: 7 secret object(s) seen after reference run ['secret/default/internal-mongodb-cluster-users', 'secret/default/mongodb-cluster-mongodb-encryption-key', 'secret/default/mongodb-cluster-mongodb-keyfile', 'secret/default/mongodb-cluster-secrets', 'secret/default/mongodb-cluster-ssl', 'secret/default/mongodb-cluster-ssl-internal', 'secret/default/percona-server-mongodb-operator-token-gqtsx'] but 6 secret object(s) seen after testing run ['secret/default/internal-mongodb-cluster-users', 'secret/default/mongodb-cluster-mongodb-encryption-key', 'secret/default/mongodb-cluster-mongodb-keyfile', 'secret/default/mongodb-cluster-secrets', 'secret/default/mongodb-cluster-ssl', 'secret/default/percona-server-mongodb-operator-token-gg455']
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

#### stale-state bug 1: [percona-server-mongodb-operator-430](https://jira.percona.com/browse/K8SPSMDB-430)
```
python3 reproduce_bugs.py -c mongodb-operator -b stale-state-1
```
If reproduced, you will see errors reported by Sieve including
```
State-update summaries inconsistency: persistentvolumeclaim/default/mongod-data-mongodb-cluster-rs0-0 ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: persistentvolumeclaim/default/mongod-data-mongodb-cluster-rs0-0 DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

#### stale-state bug 2: [percona-server-mongodb-operator-433](https://jira.percona.com/browse/K8SPSMDB-433)
```
python3 reproduce_bugs.py -c mongodb-operator -b stale-state-2
```
If reproduced, you will see errors reported by Sieve including
```
State-update summaries inconsistency: pod/default/mongodb-cluster-cfg-0 ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: pod/default/mongodb-cluster-cfg-0 DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

#### stale-state bug 3: [percona-server-mongodb-operator-438](https://jira.percona.com/browse/K8SPSMDB-438)
```
python3 reproduce_bugs.py -c mongodb-operator -b stale-state-3
```
If reproduced, you will see errors reported by Sieve including
```
State-update summaries inconsistency: pod/default/mongodb-cluster-rs0-arbiter-0 ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: pod/default/mongodb-cluster-rs0-arbiter-0 DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

#### unobserved-state bug 1: [percona-server-mongodb-operator-585](https://jira.percona.com/browse/K8SPSMDB-585)
```
python3 reproduce_bugs.py -c mongodb-operator -b unobserved-state-1
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - fewer objects than reference: persistentvolumeclaim/default/mongod-data-mongodb-cluster-rs0-4 is seen after reference run, but not seen after testing run
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

### [nifikop](https://github.com/Orange-OpenSource/nifikop)

#### [orange-opensource-nifikop-130](https://github.com/Orange-OpenSource/nifikop/issues/130)
```
python3 reproduce_bugs.py -c nifikop-operator -b intermediate-state-1
```
If reproduced, you will see errors reported by Sieve including
```
State-update summaries inconsistency: pod/default/simplenifi-1-node* ADDED inconsistency: 2 event(s) seen during reference run, but 1 seen during testing run
State-update summaries inconsistency: pod/default/simplenifi-1-node* DELETED inconsistency: 1 event(s) seen during reference run, but 0 seen during testing run
```
The bug was found in commit `1546e0242107bf2f2c1256db50f47c79956dd1c6`.

### [rabbitmq-operator](https://github.com/rabbitmq/cluster-operator)

#### intermediate-state bug 1: [rabbitmq-cluster-operator-782](https://github.com/rabbitmq/cluster-operator/issues/782)
```
python3 reproduce_bugs.py -c rabbitmq-operator -b intermediate-state-1
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - object field has a different value: persistentvolumeclaim/default/persistence-rabbitmq-cluster-server-0["spec"]["resources"]["requests"]["storage"] is 15Gi after reference run, but 10Gi after testing run
End state inconsistency - object field has a different value: persistentvolumeclaim/default/persistence-rabbitmq-cluster-server-0["status"]["capacity"]["storage"] is 15Gi after reference run, but 10Gi after testing run
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

#### stale-state bug 1: [rabbitmq-cluster-operator-648](https://github.com/rabbitmq/cluster-operator/issues/648)
```
python3 reproduce_bugs.py -c rabbitmq-operator -b stale-state-1
```
If reproduced, you will see errors reported by Sieve including
```
State-update summaries inconsistency: pod/default/rabbitmq-cluster-server-0 ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: pod/default/rabbitmq-cluster-server-0 DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

#### stale-state bug 2: [rabbitmq-cluster-operator-653](https://github.com/rabbitmq/cluster-operator/issues/653)
```
python3 reproduce_bugs.py -c rabbitmq-operator -b stale-state-2
```
If reproduced, you will see errors reported by Sieve including
```
State-update summaries inconsistency: statefulset/default/rabbitmq-cluster-server ADDED inconsistency: 2 event(s) seen during reference run, but 4 seen during testing run
State-update summaries inconsistency: statefulset/default/rabbitmq-cluster-server DELETED inconsistency: 1 event(s) seen during reference run, but 3 seen during testing run
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

#### unobserved-state bug 1: [rabbitmq-cluster-operator-758](https://github.com/rabbitmq/cluster-operator/issues/758)
```
python3 reproduce_bugs.py -c rabbitmq-operator -b unobserved-state-1
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - fewer objects than reference: 4 pod object(s) seen after reference run ['pod/default/rabbitmq-cluster-server-0', 'pod/default/rabbitmq-cluster-server-1', 'pod/default/rabbitmq-cluster-server-2', 'pod/default/rabbitmq-operator-b7d5945b-tsbpq'] but 3 pod object(s) seen after testing run ['pod/default/rabbitmq-cluster-server-0', 'pod/default/rabbitmq-cluster-server-1', 'pod/default/rabbitmq-operator-757bbb7678-lhmgd']
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

### [xtradb-operator](https://github.com/percona/percona-xtradb-cluster-operator)

#### intermediate-state bug 1: [percona-xtradb-cluster-operator-896](https://jira.percona.com/browse/K8SPXC-896)
```
python3 reproduce_bugs.py -c xtradb-operator -b intermediate-state-1
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - fewer objects than reference: 5 secret object(s) seen after reference run ['secret/default/internal-xtradb-cluster', 'secret/default/percona-xtradb-cluster-operator-token-cprgn', 'secret/default/xtradb-cluster-secrets', 'secret/default/xtradb-cluster-ssl', 'secret/default/xtradb-cluster-ssl-internal'] but 4 secret object(s) seen after testing run ['secret/default/internal-xtradb-cluster', 'secret/default/percona-xtradb-cluster-operator-token-m8k2j', 'secret/default/xtradb-cluster-secrets', 'secret/default/xtradb-cluster-ssl']
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

#### intermediate-state bug 2: [percona-xtradb-cluster-operator-897](https://jira.percona.com/browse/K8SPXC-897)
```
python3 reproduce_bugs.py -c xtradb-operator -b intermediate-state-2
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - fewer objects than reference: 5 secret object(s) seen after reference run ['secret/default/internal-xtradb-cluster', 'secret/default/percona-xtradb-cluster-operator-token-gqhsf', 'secret/default/xtradb-cluster-secrets', 'secret/default/xtradb-cluster-ssl', 'secret/default/xtradb-cluster-ssl-internal'] but 4 secret object(s) seen after testing run ['secret/default/internal-xtradb-cluster', 'secret/default/percona-xtradb-cluster-operator-token-6crll', 'secret/default/xtradb-cluster-secrets', 'secret/default/xtradb-cluster-ssl']
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

#### stale-state bug 1: [percona-xtradb-cluster-operator-716](https://jira.percona.com/browse/K8SPXC-716)
```
python3 reproduce_bugs.py -c xtradb-operator -b stale-state-1
```
If reproduced, you will see errors reported by Sieve including
```
State-update summaries inconsistency: persistentvolumeclaim/default/datadir-xtradb-cluster-pxc-0 ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: persistentvolumeclaim/default/datadir-xtradb-cluster-pxc-0 DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

#### stale-state bug 2: [percona-xtradb-cluster-operator-725](https://jira.percona.com/browse/K8SPXC-725)
```
python3 reproduce_bugs.py -c xtradb-operator -b stale-state-2
```
If reproduced, you will see errors reported by Sieve including
```
State-update summaries inconsistency: pod/default/xtradb-cluster-haproxy-0 ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: pod/default/xtradb-cluster-haproxy-0 DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

#### stale-state bug 3: [percona-xtradb-cluster-operator-763](https://jira.percona.com/browse/K8SPXC-763)
```
python3 reproduce_bugs.py -c xtradb-operator -b stale-state-3
```
If reproduced, you will see errors reported by Sieve including
```
State-update summaries inconsistency: pod/default/xtradb-cluster-proxysql-0 ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: pod/default/xtradb-cluster-proxysql-0 DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

#### unobserved-state bug 1: [percona-xtradb-cluster-operator-918](https://jira.percona.com/browse/K8SPXC-918)
```
python3 reproduce_bugs.py -c xtradb-operator -b unobserved-state-1
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - fewer objects than reference: persistentvolumeclaim/default/datadir-xtradb-cluster-pxc-3 is seen after reference run, but not seen after testing run
End state inconsistency - fewer objects than reference: persistentvolumeclaim/default/datadir-xtradb-cluster-pxc-4 is seen after reference run, but not seen after testing run
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

### [yugabyte-operator](https://github.com/yugabyte/yugabyte-operator)

#### stale-state bug 1: [yugabyte-operator-35](https://github.com/yugabyte/yugabyte-operator/issues/35)
```
python3 reproduce_bugs.py -c yugabyte-operator -b stale-state-1
```
If reproduced, you will see errors reported by Sieve including
```
State-update summaries inconsistency: secret/default/yb-master-yugabyte-tls-cert ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: secret/default/yb-master-yugabyte-tls-cert DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
State-update summaries inconsistency: secret/default/yb-tserver-yugabyte-tls-cert ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: secret/default/yb-tserver-yugabyte-tls-cert DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```
This bug was found in commit `966ef1978ed5d714119548b2c4343925fe49f882`.

#### stale-state bug 2: [yugabyte-operator-36](https://github.com/yugabyte/yugabyte-operator/issues/36)
```
python3 reproduce_bugs.py -c yugabyte-operator -b stale-state-2
```
If reproduced, you will see errors reported by Sieve including
```
State-update summaries inconsistency: service/default/yb-tserver-ui ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: service/default/yb-tserver-ui DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```
This bug was found in commit `966ef1978ed5d714119548b2c4343925fe49f882` with the prerequisite 
[fix](https://github.com/yugabyte/yugabyte-operator/pull/34).

#### unobserved-state bug 1 [yugabyte-operator-39](https://github.com/yugabyte/yugabyte-operator/issues/39)
```
python3 reproduce_bugs.py -c yugabyte-operator -b unobserved-state-1
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - fewer objects than reference: 8 pod object(s) seen after reference run ['pod/default/yb-master-0', 'pod/default/yb-master-1', 'pod/default/yb-master-2', 'pod/default/yb-tserver-0', 'pod/default/yb-tserver-1', 'pod/default/yb-tserver-2', 'pod/default/yb-tserver-3', 'pod/default/yugabyte-operator-86f6465d9b-7vpz2'] but 7 pod object(s) seen after testing run ['pod/default/yb-master-0', 'pod/default/yb-master-1', 'pod/default/yb-master-2', 'pod/default/yb-tserver-0', 'pod/default/yb-tserver-1', 'pod/default/yb-tserver-2', 'pod/default/yugabyte-operator-649c78d854-vms75']
```
This bug was found in commit `966ef1978ed5d714119548b2c4343925fe49f882`.

### [zookeeper-operator](https://github.com/pravega/zookeeper-operator)

#### stale-state bug 1: [pravega-zookeeper-operator-312](https://github.com/pravega/zookeeper-operator/issues/312)
```
python3 reproduce_bugs.py -c zookeeper-operator -b stale-state-1
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - more object fields than reference: persistentvolumeclaim/default/data-zookeeper-cluster-0["metadata"]["deletionTimestamp"] not seen after reference run, but is 2022-04-01T09:15:46Z after testing run
```
The bug was found in commit `cda03d2f270bdfb51372192766123904f6d88278`.

#### stale-state bug 2: [pravega-zookeeper-operator-314](https://github.com/pravega/zookeeper-operator/issues/314)
```
python3 reproduce_bugs.py -c zookeeper-operator -b stale-state-2
```
If reproduced, you will see errors reported by Sieve including
```
State-update summaries inconsistency: persistentvolumeclaim/default/data-zookeeper-cluster-1 ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: persistentvolumeclaim/default/data-zookeeper-cluster-1 DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
State-update summaries inconsistency: pod/default/zookeeper-cluster-1 ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: pod/default/zookeeper-cluster-1 DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```
The bug was found in commit `cda03d2f270bdfb51372192766123904f6d88278`.

## 8 indirect bugs
Note that Sieve does NOT guarantee to consistently reproduce the following indirect bugs as these bugs are not directly triggered by the test plans generated by our Sieve.

### [cassandra-operator](https://github.com/instaclustr/cassandra-operator)

#### indirect bug 1: [instaclustr-cassandra-operator-400](https://github.com/instaclustr/cassandra-operator/issues/400)
```
python3 reproduce_bugs.py -c cassandra-operator -b indirect-1
```
If reproduced, you will see errors reported by Sieve including
```
Error from the workload: error: hard timeout: cassandra-test-cluster-dc1-rack1-1 does not become Terminated within 600 seconds
```

#### indirect bug 2: [instaclustr-cassandra-operator-410](https://github.com/instaclustr/cassandra-operator/issues/410)
```
python3 reproduce_bugs.py -c cassandra-operator -b indirect-2
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - object field has a different value: pod/default/cassandra-test-cluster-dc1-rack1-1["status"]["containerStatuses"][0]["ready"] is True after reference run, but False after testing run
End state inconsistency - object field has a different value: statefulset/default/cassandra-test-cluster-dc1-rack1["status"]["readyReplicas"] is 2 after reference run, but 1 after testing run
```

### [mongodb-operator](https://github.com/percona/percona-server-mongodb-operator)

#### indirect bug 1: [percona-server-mongodb-operator-434](https://jira.percona.com/browse/K8SPSMDB-434)
```
python3 reproduce_bugs.py -c mongodb-operator -b indirect-1
```
If reproduced, you will see errors reported by Sieve including
```
Exception from controller: Observed a panic: "invalid memory address or nil pointer dereference" (runtime error: invalid memory address or nil pointer dereference)
```

#### indirect bug 2: [percona-server-mongodb-operator-590](https://jira.percona.com/browse/K8SPSMDB-590)
```
python3 reproduce_bugs.py -c mongodb-operator -b indirect-2
```
If reproduced, you will see errors reported by Sieve including
```
State-update summaries inconsistency: secret/default/mongodb-cluster-ssl ADDED inconsistency: 2 event(s) seen during reference run, but 
3 seen during testing run                                                                                                               
State-update summaries inconsistency: secret/default/mongodb-cluster-ssl DELETED inconsistency: 1 event(s) seen during reference run, bu
t 2 seen during testing run                                                                                                             
State-update summaries inconsistency: secret/default/mongodb-cluster-ssl-internal ADDED inconsistency: 2 event(s) seen during reference 
run, but 3 seen during testing run                                                                                                      
State-update summaries inconsistency: secret/default/mongodb-cluster-ssl-internal DELETED inconsistency: 1 event(s) seen during referenc
e run, but 2 seen during testing run
```

#### indirect bug 3: [percona-server-mongodb-operator-591](https://jira.percona.com/browse/K8SPSMDB-591)
```
python3 reproduce_bugs.py -c mongodb-operator -b indirect-3
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - object field has a different value: perconaservermongodb/default/mongodb-cluster["status"]["state"] is ready after learning run, but error after testing run
End state inconsistency - fewer object fields than reference: perconaservermongodb/default/mongodb-cluster["status"]["replsets"]["rs0"]["added_as_shard"] is True after learning run, but not seen after testing run
```

### [yugabyte-operator](https://github.com/yugabyte/yugabyte-operator)

#### indirect bug 1: [yugabyte-operator-33](https://github.com/yugabyte/yugabyte-operator/issues/33)
```
python3 reproduce_bugs.py -c yugabyte-operator -b indirect-1
```
If reproduced, you will see errors reported by Sieve including
```
Error from the workload: error: cmd 'kubectl patch YBCluster example-ybcluster --type merge -p='{"spec":{"tserver":{"tserverUIPort": 0}}}'' return non-zero code 1
Error from the workload: error: hard timeout: yb-tserver-ui does not become non-exist within 600 seconds
```

#### indirect bug 2: [yugabyte-operator-43](https://github.com/yugabyte/yugabyte-operator/issues/43)
```
python3 reproduce_bugs.py -c yugabyte-operator -b indirect-2
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - object field has a different value: pod/default/yb-master-2["status"]["containerStatuses"][0]["state"]["runni$g"] is {'StartedAt': '2022-02-04T08:50:21Z'} after reference run, but None after testing run
```

### [zookeeper-operator](https://github.com/pravega/zookeeper-operator)

#### indirect bug 1: [zookeeper-operator-410](https://github.com/pravega/zookeeper-operator/issues/410)
```
python3 reproduce_bugs.py -c zookeeper-operator -b indirect-1
```
If reproduced, you will see errors reported by Sieve including
```
State-update summaries inconsistency: configmap/default/zookeeper-cluster-configmap ADDED inconsistency: 2 event(s) seen during referenc
e run, but 3 seen during testing run                                                                                                    
State-update summaries inconsistency: configmap/default/zookeeper-cluster-configmap DELETED inconsistency: 1 event(s) seen during refere
nce run, but 2 seen during testing run
```
