# Bug Finding

For each reproduced bug, you will see a test result json file as shown in the last column of `bug_reproduction_stats.tsv`.
This json file contains the errors detected by Sieve (see the `detected_errors` field).
The errors can be common errors (like timeout) and inconsistencies detected by the differential oracles.
We present the expected errors caused by each bug (if reproduced) to help you evaluate whether the bug is correctly reproduced.
Sieve might detect many different errors for the same bug,
we only present one or two representative errors here.

### [cass-operator](https://github.com/k8ssandra/cass-operator)

#### intermediate-state-1: [k8ssandra-cass-operator-1023](https://k8ssandra.atlassian.net/browse/K8SSAND-1023)
The `sieve_test_results/cass-operator-recreate-cass-operator-intermediate-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
Error from the workload: error: hard timeout: cluster1-cassandra-datacenter-default-sts-0 does not become Running within 1000 seconds
```

<!-- #### [datastax-cass-operator-412](https://github.com/datastax/cass-operator/issues/412) -->
#### stale-state-1: [k8ssandra-cass-operator-559](https://k8ssandra.atlassian.net/browse/K8SSAND-559)
The `sieve_test_results/cass-operator-recreate-cass-operator-stale-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
End state inconsistency - more object fields than reference: persistentvolumeclaim/default/server-data-cluster1-cassandra-datacenter-default-sts-0["metadata"]["deletionTimestamp"] not seen after reference run, but is 2022-04-01T05:31:17Z after testing run
```
Note that the timestamp can be different in your run.

### [cassandra-operator](https://github.com/instaclustr/cassandra-operator)

#### stale-state-1: [instaclustr-cassandra-operator-402](https://github.com/instaclustr/cassandra-operator/issues/402)
The `sieve_test_results/cassandra-operator-recreate-cassandra-operator-stale-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
End state inconsistency - more object fields than reference: persistentvolumeclaim/default/data-volume-cassandra-test-cluster-dc1-rack1-0["metadata"]["deletionTimestamp"] not seen after reference run, but is 2022-04-01T04:22:06Z after testing run
```
Note that the timestamp can be different in your run.

#### stale-state-2: [instaclustr-cassandra-operator-407](https://github.com/instaclustr/cassandra-operator/issues/407)
The `sieve_test_results/cassandra-operator-scaledown-scaleup-cassandra-operator-stale-state-2.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
End state inconsistency - more object fields than reference: persistentvolumeclaim/default/data-volume-cassandra-test-cluster-dc1-rack1-1["metadata"]["deletionTimestamp"] not seen after reference run, but is 2022-04-01T04:34:00Z after testing run
```
Note that the timestamp can be different in your run.

#### unobserved-state-1: [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398)
The `sieve_test_results/cassandra-operator-scaledown-scaleup-cassandra-operator-unobserved-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
End state inconsistency - object field has a different value: pod/default/cassandra-test-cluster-dc1-rack1-1["status"]["containerStatuses"][0]["ready"] is True after reference run, but False after testing run
```

### [casskop](https://github.com/Orange-OpenSource/casskop)

#### intermediate-state-1: [orange-opensource-casskop-370](https://github.com/Orange-OpenSource/casskop/issues/370)
The `sieve_test_results/casskop-operator-scaledown-to-zero-casskop-intermediate-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
End state inconsistency - more objects than reference: persistentvolumeclaim/default/data-cassandra-cluster-dc1-rack1-1 is not seen after reference run, but seen after testing run
End state inconsistency - object field has a different value: cassandracluster/default/cassandra-cluster["status"]["cassandraRackStatus"]["dc1-rack1"]["cassandraLastAction"]["status"] is Done after reference run, but ToDo after testing run
```

#### stale-state-1: [orange-opensource-casskop-316](https://github.com/Orange-OpenSource/casskop/issues/316)
The `sieve_test_results/casskop-operator-recreate-casskop-stale-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
End state inconsistency - more object fields than reference: persistentvolumeclaim/default/data-cassandra-cluster-dc1-rack1-0["metadata"]["deletionTimestamp"] not seen after reference run, but is 2022-04-01T05:46:44Z after testing run
```
Note that the timestamp can be different in your run.

#### stale-state-2: [orange-opensource-casskop-321](https://github.com/Orange-OpenSource/casskop/issues/321)
The `sieve_test_results/casskop-operator-reducepdb-casskop-stale-state-2.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
State-update summaries inconsistency: poddisruptionbudget/default/cassandra-cluster ADDED inconsistency: 2 event(s) seen during reference run, but 4 seen during testing run
State-update summaries inconsistency: poddisruptionbudget/default/cassandra-cluster DELETED inconsistency: 1 event(s) seen during reference run, but 3 seen during testing run
```

#### unobserved-state-1: [orange-opensource-casskop-342](https://github.com/Orange-OpenSource/casskop/issues/342)
The `sieve_test_results/casskop-operator-scaledown-to-zero-casskop-unobserved-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
End state inconsistency - more objects than reference: 2 pod object(s) seen after reference run ['pod/default/cassandra-cluster-dc1-rack1-0', 'pod/default/casskop-operator-546674cfdd-z486x'] but 3 pod object(s) seen after testing run ['pod/default/cassandra-cluster-dc1-rack1-0', 'pod/default/cassandra-cluster-dc1-rack1-1', 'pod/default/casskop-operator-67fdccf6f4-s6cgt']
```
Note that the randomly generated pod name (e.g., `pod/default/casskop-operator-546674cfdd-z486x`) can be different in your run but the pod numbers (`2` and `3`) should be the same.

### [mongodb-operator](https://github.com/percona/percona-server-mongodb-operator)

#### intermediate-state-1: [percona-server-mongodb-operator-578](https://jira.percona.com/browse/K8SPSMDB-578)
The `sieve_test_results/mongodb-operator-disable-enable-shard-mongodb-operator-intermediate-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
End state inconsistency - fewer objects than reference: 7 secret object(s) seen after reference run ['secret/default/internal-mongodb-cluster-users', 'secret/default/mongodb-cluster-mongodb-encryption-key', 'secret/default/mongodb-cluster-mongodb-keyfile', 'secret/default/mongodb-cluster-secrets', 'secret/default/mongodb-cluster-ssl', 'secret/default/mongodb-cluster-ssl-internal', 'secret/default/percona-server-mongodb-operator-token-4pbxq'] but 6 secret object(s) seen after testing run ['secret/default/internal-mongodb-cluster-users', 'secret/default/mongodb-cluster-mongodb-encryption-key', 'secret/default/mongodb-cluster-mongodb-keyfile', 'secret/default/mongodb-cluster-secrets', 'secret/default/mongodb-cluster-ssl', 'secret/default/percona-server-mongodb-operator-token-rkglb']
```
Note that the randomly generated secret name (e.g., `secret/default/percona-server-mongodb-operator-token-4pbxq`) can be different in your run but the secret numbers (`7` and `6`) should be the same.

#### intermediate-state-2: [percona-server-mongodb-operator-579](https://jira.percona.com/browse/K8SPSMDB-579)
The `sieve_test_results/mongodb-operator-run-cert-manager-mongodb-operator-intermediate-state-2.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
End state inconsistency - fewer objects than reference: 7 secret object(s) seen after reference run ['secret/default/internal-mongodb-cluster-users', 'secret/default/mongodb-cluster-mongodb-encryption-key', 'secret/default/mongodb-cluster-mongodb-keyfile', 'secret/default/mongodb-cluster-secrets', 'secret/default/mongodb-cluster-ssl', 'secret/default/mongodb-cluster-ssl-internal', 'secret/default/percona-server-mongodb-operator-token-gqtsx'] but 6 secret object(s) seen after testing run ['secret/default/internal-mongodb-cluster-users', 'secret/default/mongodb-cluster-mongodb-encryption-key', 'secret/default/mongodb-cluster-mongodb-keyfile', 'secret/default/mongodb-cluster-secrets', 'secret/default/mongodb-cluster-ssl', 'secret/default/percona-server-mongodb-operator-token-gg455']
```
Note that the randomly generated secret name (e.g., `secret/default/percona-server-mongodb-operator-token-gqtsx`) can be different in your run but the secret numbers (`7` and `6`) should be the same.

#### stale-state-1: [percona-server-mongodb-operator-430](https://jira.percona.com/browse/K8SPSMDB-430)
The `sieve_test_results/mongodb-operator-recreate-mongodb-operator-stale-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
State-update summaries inconsistency: persistentvolumeclaim/default/mongod-data-mongodb-cluster-rs0-0 ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: persistentvolumeclaim/default/mongod-data-mongodb-cluster-rs0-0 DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```

#### stale-state-2: [percona-server-mongodb-operator-433](https://jira.percona.com/browse/K8SPSMDB-433)
The `sieve_test_results/mongodb-operator-disable-enable-shard-mongodb-operator-stale-state-2.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
State-update summaries inconsistency: pod/default/mongodb-cluster-cfg-0 ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: pod/default/mongodb-cluster-cfg-0 DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```

#### stale-state-3: [percona-server-mongodb-operator-438](https://jira.percona.com/browse/K8SPSMDB-438)
The `sieve_test_results/mongodb-operator-disable-enable-arbiter-mongodb-operator-stale-state-3.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
State-update summaries inconsistency: pod/default/mongodb-cluster-rs0-arbiter-0 ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: pod/default/mongodb-cluster-rs0-arbiter-0 DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```

#### unobserved-state-1: [percona-server-mongodb-operator-585](https://jira.percona.com/browse/K8SPSMDB-585)
The `sieve_test_results/mongodb-operator-disable-enable-arbiter-mongodb-operator-unobserved-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
End state inconsistency - fewer objects than reference: persistentvolumeclaim/default/mongod-data-mongodb-cluster-rs0-4 is seen after reference run, but not seen after testing run
```

### [nifikop](https://github.com/Orange-OpenSource/nifikop)

#### [orange-opensource-nifikop-130](https://github.com/Orange-OpenSource/nifikop/issues/130)
The `sieve_test_results/nifikop-operator-change-config-nifikop-intermediate-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
State-update summaries inconsistency: pod/default/simplenifi-1-node* ADDED inconsistency: 2 event(s) seen during reference run, but 1 seen during testing run
State-update summaries inconsistency: pod/default/simplenifi-1-node* DELETED inconsistency: 1 event(s) seen during reference run, but 0 seen during testing run
```

### [rabbitmq-operator](https://github.com/rabbitmq/cluster-operator)

#### intermediate-state-1: [rabbitmq-cluster-operator-782](https://github.com/rabbitmq/cluster-operator/issues/782)
The `sieve_test_results/rabbitmq-operator-resize-pvc-rabbitmq-operator-intermediate-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
End state inconsistency - object field has a different value: persistentvolumeclaim/default/persistence-rabbitmq-cluster-server-0["spec"]["resources"]["requests"]["storage"] is 15Gi after reference run, but 10Gi after testing run
End state inconsistency - object field has a different value: persistentvolumeclaim/default/persistence-rabbitmq-cluster-server-0["status"]["capacity"]["storage"] is 15Gi after reference run, but 10Gi after testing run
```

#### stale-state-1: [rabbitmq-cluster-operator-648](https://github.com/rabbitmq/cluster-operator/issues/648)
The `sieve_test_results/rabbitmq-operator-recreate-rabbitmq-operator-stale-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
State-update summaries inconsistency: pod/default/rabbitmq-cluster-server-0 ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: pod/default/rabbitmq-cluster-server-0 DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```

#### stale-state-2: [rabbitmq-cluster-operator-653](https://github.com/rabbitmq/cluster-operator/issues/653)
The `sieve_test_results/rabbitmq-operator-resize-pvc-rabbitmq-operator-stale-state-2.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
State-update summaries inconsistency: statefulset/default/rabbitmq-cluster-server ADDED inconsistency: 2 event(s) seen during reference run, but 4 seen during testing run
State-update summaries inconsistency: statefulset/default/rabbitmq-cluster-server DELETED inconsistency: 1 event(s) seen during reference run, but 3 seen during testing run
```

#### unobserved-state-1: [rabbitmq-cluster-operator-758](https://github.com/rabbitmq/cluster-operator/issues/758)
The `sieve_test_results/rabbitmq-operator-scaleup-scaledown-rabbitmq-operator-unobserved-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
End state inconsistency - fewer objects than reference: 4 pod object(s) seen after reference run ['pod/default/rabbitmq-cluster-server-0', 'pod/default/rabbitmq-cluster-server-1', 'pod/default/rabbitmq-cluster-server-2', 'pod/default/rabbitmq-operator-b7d5945b-tsbpq'] but 3 pod object(s) seen after testing run ['pod/default/rabbitmq-cluster-server-0', 'pod/default/rabbitmq-cluster-server-1', 'pod/default/rabbitmq-operator-757bbb7678-lhmgd']
```
Note that the randomly generated pod name (e.g., `pod/default/rabbitmq-operator-757bbb7678-lhmgd`) can be different in your run but the pod numbers (`4` and `3`) should be the same.

### [xtradb-operator](https://github.com/percona/percona-xtradb-cluster-operator)

#### intermediate-state-1: [percona-xtradb-cluster-operator-896](https://jira.percona.com/browse/K8SPXC-896)
The `sieve_test_results/xtradb-operator-disable-enable-proxysql-xtradb-operator-intermediate-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
End state inconsistency - fewer objects than reference: 5 secret object(s) seen after reference run ['secret/default/internal-xtradb-cluster', 'secret/default/percona-xtradb-cluster-operator-token-cprgn', 'secret/default/xtradb-cluster-secrets', 'secret/default/xtradb-cluster-ssl', 'secret/default/xtradb-cluster-ssl-internal'] but 4 secret object(s) seen after testing run ['secret/default/internal-xtradb-cluster', 'secret/default/percona-xtradb-cluster-operator-token-m8k2j', 'secret/default/xtradb-cluster-secrets', 'secret/default/xtradb-cluster-ssl']
```
Note that the randomly generated secret name (e.g., `secret/default/percona-xtradb-cluster-operator-token-cprgn`) can be different in your run but the secret numbers (`5` and `6`) should be the same.

#### intermediate-state-2: [percona-xtradb-cluster-operator-897](https://jira.percona.com/browse/K8SPXC-897)
The `sieve_test_results/xtradb-operator-run-cert-manager-xtradb-operator-intermediate-state-2.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
End state inconsistency - fewer objects than reference: 5 secret object(s) seen after reference run ['secret/default/internal-xtradb-cluster', 'secret/default/percona-xtradb-cluster-operator-token-gqhsf', 'secret/default/xtradb-cluster-secrets', 'secret/default/xtradb-cluster-ssl', 'secret/default/xtradb-cluster-ssl-internal'] but 4 secret object(s) seen after testing run ['secret/default/internal-xtradb-cluster', 'secret/default/percona-xtradb-cluster-operator-token-6crll', 'secret/default/xtradb-cluster-secrets', 'secret/default/xtradb-cluster-ssl']
```
Note that the randomly generated secret name (e.g., `secret/default/percona-xtradb-cluster-operator-token-gqhsf`) can be different in your run but the secret numbers (`5` and `6`) should be the same.

#### stale-state-1: [percona-xtradb-cluster-operator-716](https://jira.percona.com/browse/K8SPXC-716)
The `sieve_test_results/xtradb-operator-recreate-xtradb-operator-stale-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
State-update summaries inconsistency: persistentvolumeclaim/default/datadir-xtradb-cluster-pxc-0 ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: persistentvolumeclaim/default/datadir-xtradb-cluster-pxc-0 DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```

#### stale-state-2: [percona-xtradb-cluster-operator-725](https://jira.percona.com/browse/K8SPXC-725)
The `sieve_test_results/xtradb-operator-disable-enable-haproxy-xtradb-operator-stale-state-2.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
State-update summaries inconsistency: pod/default/xtradb-cluster-haproxy-0 ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: pod/default/xtradb-cluster-haproxy-0 DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```

#### stale-state-3: [percona-xtradb-cluster-operator-763](https://jira.percona.com/browse/K8SPXC-763)
The `sieve_test_results/xtradb-operator-disable-enable-proxysql-xtradb-operator-stale-state-3.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
State-update summaries inconsistency: pod/default/xtradb-cluster-proxysql-0 ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: pod/default/xtradb-cluster-proxysql-0 DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```

#### unobserved-state-1: [percona-xtradb-cluster-operator-918](https://jira.percona.com/browse/K8SPXC-918)
The `sieve_test_results/xtradb-operator-scaleup-scaledown-xtradb-operator-unobserved-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
End state inconsistency - fewer objects than reference: persistentvolumeclaim/default/datadir-xtradb-cluster-pxc-3 is seen after reference run, but not seen after testing run
End state inconsistency - fewer objects than reference: persistentvolumeclaim/default/datadir-xtradb-cluster-pxc-4 is seen after reference run, but not seen after testing run
```

### [yugabyte-operator](https://github.com/yugabyte/yugabyte-operator)

#### stale-state-1: [yugabyte-operator-35](https://github.com/yugabyte/yugabyte-operator/issues/35)
The `sieve_test_results/yugabyte-operator-disable-enable-tls-yugabyte-operator-stale-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
State-update summaries inconsistency: secret/default/yb-master-yugabyte-tls-cert ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: secret/default/yb-master-yugabyte-tls-cert DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
State-update summaries inconsistency: secret/default/yb-tserver-yugabyte-tls-cert ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: secret/default/yb-tserver-yugabyte-tls-cert DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```

#### stale-state-2: [yugabyte-operator-36](https://github.com/yugabyte/yugabyte-operator/issues/36)
The `sieve_test_results/yugabyte-operator-disable-enable-tuiport-yugabyte-operator-stale-state-2.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
State-update summaries inconsistency: service/default/yb-tserver-ui ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: service/default/yb-tserver-ui DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```

#### unobserved-state-1 [yugabyte-operator-39](https://github.com/yugabyte/yugabyte-operator/issues/39)
The `sieve_test_results/yugabyte-operator-scaleup-scaledown-tserver-yugabyte-operator-unobserved-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
End state inconsistency - fewer objects than reference: 8 pod object(s) seen after reference run ['pod/default/yb-master-0', 'pod/default/yb-master-1', 'pod/default/yb-master-2', 'pod/default/yb-tserver-0', 'pod/default/yb-tserver-1', 'pod/default/yb-tserver-2', 'pod/default/yb-tserver-3', 'pod/default/yugabyte-operator-86f6465d9b-7vpz2'] but 7 pod object(s) seen after testing run ['pod/default/yb-master-0', 'pod/default/yb-master-1', 'pod/default/yb-master-2', 'pod/default/yb-tserver-0', 'pod/default/yb-tserver-1', 'pod/default/yb-tserver-2', 'pod/default/yugabyte-operator-649c78d854-vms75']
```
Note that the randomly generated pod name (e.g., `pod/default/yugabyte-operator-86f6465d9b-7vpz2`) can be different in your run but the pod numbers (`8` and `7`) should be the same.

### [zookeeper-operator](https://github.com/pravega/zookeeper-operator)

#### stale-state-1: [pravega-zookeeper-operator-312](https://github.com/pravega/zookeeper-operator/issues/312)
The `sieve_test_results/zookeeper-operator-recreate-zookeeper-operator-stale-state-1.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
End state inconsistency - more object fields than reference: persistentvolumeclaim/default/data-zookeeper-cluster-0["metadata"]["deletionTimestamp"] not seen after reference run, but is 2022-04-01T09:15:46Z after testing run
```
Note that the timestamp can be different in your run.

#### stale-state-2: [pravega-zookeeper-operator-314](https://github.com/pravega/zookeeper-operator/issues/314)
The `sieve_test_results/zookeeper-operator-scaledown-scaleup-zookeeper-operator-stale-state-2.yaml.json` is supposed to contain the following error in its `detected_errors` field:
```
State-update summaries inconsistency: persistentvolumeclaim/default/data-zookeeper-cluster-1 ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: persistentvolumeclaim/default/data-zookeeper-cluster-1 DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
State-update summaries inconsistency: pod/default/zookeeper-cluster-1 ADDED inconsistency: 2 event(s) seen during reference run, but 3 seen during testing run
State-update summaries inconsistency: pod/default/zookeeper-cluster-1 DELETED inconsistency: 1 event(s) seen during reference run, but 2 seen during testing run
```

## Reproducing 8 indirect bugs
Note that Sieve does NOT guarantee to consistently reproduce the 8 indirect bugs as these bugs are not directly triggered by the test plans generated by our Sieve.
For the 8 indirect bugs, `reproduce_bugs.py` will run some extra steps (e.g., change testing configuration) to reproduce the bug, or make it easier to reproduce.

### [cassandra-operator](https://github.com/instaclustr/cassandra-operator)

#### indirect-1: [instaclustr-cassandra-operator-400](https://github.com/instaclustr/cassandra-operator/issues/400)
```
python3 reproduce_bugs.py -p cassandra-operator -b indirect-1
```
If reproduced, you will see errors reported by Sieve including
```
Error from the workload: error: hard timeout: cassandra-test-cluster-dc1-rack1-1 does not become Terminated within 600 seconds
```

#### indirect-2: [instaclustr-cassandra-operator-410](https://github.com/instaclustr/cassandra-operator/issues/410)
```
python3 reproduce_bugs.py -p cassandra-operator -b indirect-2
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - object field has a different value: pod/default/cassandra-test-cluster-dc1-rack1-1["status"]["containerStatuses"][0]["ready"] is True after reference run, but False after testing run
End state inconsistency - object field has a different value: statefulset/default/cassandra-test-cluster-dc1-rack1["status"]["readyReplicas"] is 2 after reference run, but 1 after testing run
```

### [mongodb-operator](https://github.com/percona/percona-server-mongodb-operator)

#### indirect-1: [percona-server-mongodb-operator-434](https://jira.percona.com/browse/K8SPSMDB-434)
```
python3 reproduce_bugs.py -p mongodb-operator -b indirect-1
```
If reproduced, you will see errors reported by Sieve including
```
Exception from controller: Observed a panic: "invalid memory address or nil pointer dereference" (runtime error: invalid memory address or nil pointer dereference)
```

#### indirect-2: [percona-server-mongodb-operator-590](https://jira.percona.com/browse/K8SPSMDB-590)
```
python3 reproduce_bugs.py -p mongodb-operator -b indirect-2
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

#### indirect-3: [percona-server-mongodb-operator-591](https://jira.percona.com/browse/K8SPSMDB-591)
```
python3 reproduce_bugs.py -p mongodb-operator -b indirect-3
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - object field has a different value: perconaservermongodb/default/mongodb-cluster["status"]["state"] is ready after learning run, but error after testing run
End state inconsistency - fewer object fields than reference: perconaservermongodb/default/mongodb-cluster["status"]["replsets"]["rs0"]["added_as_shard"] is True after learning run, but not seen after testing run
```

### [yugabyte-operator](https://github.com/yugabyte/yugabyte-operator)

#### indirect-1: [yugabyte-operator-33](https://github.com/yugabyte/yugabyte-operator/issues/33)
```
python3 reproduce_bugs.py -p yugabyte-operator -b indirect-1
```
If reproduced, you will see errors reported by Sieve including
```
Error from the workload: error: cmd 'kubectl patch YBCluster example-ybcluster --type merge -p='{"spec":{"tserver":{"tserverUIPort": 0}}}'' return non-zero code 1
Error from the workload: error: hard timeout: yb-tserver-ui does not become non-exist within 600 seconds
```

#### indirect-2: [yugabyte-operator-43](https://github.com/yugabyte/yugabyte-operator/issues/43)
```
python3 reproduce_bugs.py -p yugabyte-operator -b indirect-2
```
If reproduced, you will see errors reported by Sieve including
```
End state inconsistency - object field has a different value: pod/default/yb-master-2["status"]["containerStatuses"][0]["state"]["runni$g"] is {'StartedAt': '2022-02-04T08:50:21Z'} after reference run, but None after testing run
```

### [zookeeper-operator](https://github.com/pravega/zookeeper-operator)

#### indirect-1: [zookeeper-operator-410](https://github.com/pravega/zookeeper-operator/issues/410)
```
python3 reproduce_bugs.py -p zookeeper-operator -b indirect-1
```
If reproduced, you will see errors reported by Sieve including
```
State-update summaries inconsistency: configmap/default/zookeeper-cluster-configmap ADDED inconsistency: 2 event(s) seen during referenc
e run, but 3 seen during testing run                                                                                                    
State-update summaries inconsistency: configmap/default/zookeeper-cluster-configmap DELETED inconsistency: 1 event(s) seen during refere
nce run, but 2 seen during testing run
```
