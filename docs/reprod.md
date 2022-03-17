## Bug Reproduction

**Before reproducing the bugs**, please ensure your local environment meets all the [requirements](https://github.com/sieve-project/sieve#requirements) otherwise Sieve may not work, and set `docker_repo` in your `sieve_config.json` to `ghcr.io/sieve-project/action` (the default value).


### Intermediate state bugs

### [k8ssandra-cass-operator-1023](https://k8ssandra.atlassian.net/browse/K8SSAND-1023)
```
python3 reproduce_bugs.py -p cass-operator -b intermediate-state-1
```
If reproduced, you will see errors reported by Sieve including:
```
Error from the workload: error: hard timeout: cluster1-cassandra-datacenter-default-sts-0 does not become Running within 600 seconds
Error from the workload: error: hard timeout: cluster1-cassandra-datacenter-default-sts-0 does not become Running within 600 seconds
End state inconsistency - fewer objects than reference: 7 secret seen after learning run ['cass-operator-token-lg7rs', 'cass-operator-webhook-config', 'cassandra-datacenter-ca-keystore', 'cassandra-datacenter-keystore', 'cluster1-superuser', 'default-token-z6zxt', 'local-path-provisioner-service-account-token-j254k'] but 6 secret seen after testing run ['cass-operator-token-hr7l4', 'cass-operator-webhook-config', 'cassandra-datacenter-ca-keystore', 'cluster1-superuser', 'default-token-z6fn2', 'local-path-provisioner-service-account-token-hdl8g']
End state inconsistency - more object fields than reference: pod/default/cluster1-cassandra-datacenter-default-sts-0 status/containerStatuses/0/state/waiting not seen during learning run, but seen as {'reason': 'PodInitializing'} during testing run
End state inconsistency - more object fields than reference: pod/default/cluster1-cassandra-datacenter-default-sts-0 status/containerStatuses/1/state/waiting not seen during learning run, but seen as {'reason': 'PodInitializing'} during testing run
End state inconsistency - more object fields than reference: pod/default/cluster1-cassandra-datacenter-default-sts-0 status/initContainerStatuses/0/state/waiting not seen during learning run, but seen as {'reason': 'PodInitializing'} during testing run
End state inconsistency - object field has a different value: cassandradatacenter/default/cassandra-datacenter status/cassandraOperatorProgress is Ready during learning run, but Updating during testing run
End state inconsistency - object field has a different value: pod/default/cluster1-cassandra-datacenter-default-sts-0 status/containerStatuses/0/ready is True during learning run, but False during testing run
End state inconsistency - object field has a different value: pod/default/cluster1-cassandra-datacenter-default-sts-0 status/containerStatuses/0/started is True during learning run, but False during testing run
End state inconsistency - object field has a different value: pod/default/cluster1-cassandra-datacenter-default-sts-0 status/containerStatuses/1/ready is True during learning run, but False during testing run
End state inconsistency - object field has a different value: pod/default/cluster1-cassandra-datacenter-default-sts-0 status/containerStatuses/1/started is True during learning run, but False during testing run
...
```
The bug was found in commit `dbd4f7a10533bb2298aed0d40ea20bfd8c133da2`.

### [orange-opensource-casskop-370](https://github.com/Orange-OpenSource/casskop/issues/370)
```
python3 reproduce_bugs.py -p casskop-operator -b intermediate-state-1
```
If reproduced, you will see errors reported by Sieve including:
```
State-update summaries inconsistency: /persistentvolumeclaims/default/data-cassandra-cluster-dc1-rack1-1 DELETED inconsistency: 1 events seen during learning run, but 0 seen during testing run
End state inconsistency - more objects than reference: persistentvolumeclaim/data-cassandra-cluster-dc1-rack1-1 is not seen during learning run, but seen during testing run
```
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.

### [orange-opensource-nifikop-130](https://github.com/Orange-OpenSource/nifikop/issues/130)
```
python3 reproduce_bugs.py -p nifikop-operator -b intermediate-state-1
```
If reproduced, you will see errors reported by Sieve including:
```
State-update summaries inconsistency: /pods/default/simplenifi-1-node* ADDED inconsistency: 2 events seen during learning run, but 1 seen during testing run
State-update summaries inconsistency: /pods/default/simplenifi-1-node* DELETED inconsistency: 1 events seen during learning run, but 0 seen during testing run
```
The bug was found in commit `1546e0242107bf2f2c1256db50f47c79956dd1c6`.

### [rabbitmq-cluster-operator-782](https://github.com/rabbitmq/cluster-operator/issues/782)
```
python3 reproduce_bugs.py -p rabbitmq-operator -b intermediate-state-1
```
If reproduced, you will see errors reported by Sieve including:
```
End state inconsistency - object field has a different value: persistentvolumeclaim/default/persistence-rabbitmq-cluster-server-0 spec/resources/requests/storage is 15Gi during learning run, but 10Gi during testing run
End state inconsistency - object field has a different value: persistentvolumeclaim/default/persistence-rabbitmq-cluster-server-0 status/capacity/storage is 15Gi during learning run, but 10Gi during testing run
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

### [percona-server-mongodb-operator-578](https://jira.percona.com/browse/K8SPSMDB-578)
```
python3 reproduce_bugs.py -p mongodb-operator -b intermediate-state-1
```
If reproduced, you will see errors reported by Sieve including:
```
End state inconsistency - fewer objects than reference: 8 secret seen after learning run ['default-token-v5xjx', 'internal-mongodb-cluster-users', 'mongodb-cluster-mongodb-encryption-key', 'mongodb-cluster-mongodb-keyfile', 'mongodb-cluster-secrets', 'mongodb-cluster-ssl', 'mongodb-cluster-ssl-internal', 'percona-server-mongodb-operator-token-ntftn'] but 7 secret seen after testing run ['default-token-2ftjd', 'internal-mongodb-cluster-users', 'mongodb-cluster-mongodb-encryption-key', 'mongodb-cluster-mongodb-keyfile', 'mongodb-cluster-secrets', 'mongodb-cluster-ssl', 'percona-server-mongodb-operator-token-tgg6p']
...
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

### [percona-server-mongodb-operator-579](https://jira.percona.com/browse/K8SPSMDB-579)
```
python3 reproduce_bugs.py -p mongodb-operator -b intermediate-state-2
```
If reproduced, you will see errors reported by Sieve including:
```
End state inconsistency - fewer objects than reference: 8 secret seen after learning run ['default-token-wk4d2', 'internal-mongodb-cluster-users', 'mongodb-cluster-mongodb-encryption-key', 'mongodb-cluster-mongodb-keyfile', 'mongodb-cluster-secrets', 'mongodb-cluster-ssl', 'mongodb-cluster-ssl-internal', 'percona-server-mongodb-operator-token-8gj55'] but 7 secret seen after testing run ['default-token-9fzlj', 'internal-mongodb-cluster-users', 'mongodb-cluster-mongodb-encryption-key', 'mongodb-cluster-mongodb-keyfile', 'mongodb-cluster-secrets', 'mongodb-cluster-ssl', 'percona-server-mongodb-operator-token-qb5xx']
End state inconsistency - fewer objects than reference: certificate/mongodb-cluster-ssl-internal is seen during learning run, but not seen during testing run
...
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

### [percona-xtradb-cluster-operator-896](https://jira.percona.com/browse/K8SPXC-896)
```
python3 reproduce_bugs.py -p xtradb-operator -b intermediate-state-1
```
If reproduced, you will see errors reported by Sieve including:
```
End state inconsistency - fewer objects than reference: 6 secret seen after learning run ['default-token-nnl9s', 'internal-xtradb-cluster', 'percona-xtradb-cluster-operator-token-z9v9v', 'xtradb-cluster-secrets', 'xtradb-cluster-ssl', 'xtradb-cluster-ssl-internal'] but 5 secret seen after testing run ['default-token-v2vpv', 'internal-xtradb-cluster', 'percona-xtradb-cluster-operator-token-mkmlg', 'xtradb-cluster-secrets', 'xtradb-cluster-ssl']
...
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

### [percona-xtradb-cluster-operator-897](https://jira.percona.com/browse/K8SPXC-897)
```
python3 reproduce_bugs.py -p xtradb-operator -b intermediate-state-2
```
If reproduced, you will see errors reported by Sieve including:
```
End state inconsistency - fewer objects than reference: 6 secret seen after learning run ['default-token-sx9c2', 'internal-xtradb-cluster', 'percona-xtradb-cluster-operator-token-fl84z', 'xtradb-cluster-secrets', 'xtradb-cluster-ssl', 'xtradb-cluster-ssl-internal'] but 5 secret seen after testing run ['default-token-llvtq', 'internal-xtradb-cluster', 'percona-xtradb-cluster-operator-token-bwpzc', 'xtradb-cluster-secrets', 'xtradb-cluster-ssl']
End state inconsistency - fewer objects than reference: certificate/xtradb-cluster-ssl-internal is seen during learning run, but not seen during testing run
End state inconsistency - fewer objects than reference: certificaterequest/xtradb-cluster-ssl-internal-4197621709 is seen during learning run, but not seen during testing run
...
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

### Unobserved state bugs

### [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398)
```
python3 reproduce_bugs.py -p cassandra-operator -b unobserved-state-1
```
If reproduced, you will find
```
End state inconsistency - more object fields than reference: pod/default/cassandra-test-cluster-dc1-rack1-1 status/containerStatuses/0/state/waiting not seen during learning run, but seen as {'message': 'back-off 1m20s restarting failed container=cassandra pod=cassandra-test-cluster-dc1-rack1-1_default(e43cb7fa-d3a3-4885-856b-a9ce94462dfd)', 'reason': 'CrashLoopBackOff'} during testing run
End state inconsistency - object field has a different value: pod/default/cassandra-test-cluster-dc1-rack1-1 status/containerStatuses/0/ready is True during learning run, but False during testing run
End state inconsistency - object field has a different value: pod/default/cassandra-test-cluster-dc1-rack1-1 status/containerStatuses/0/started is True during learning run, but False during testing run
End state inconsistency - object field has a different value: statefulset/default/cassandra-test-cluster-dc1-rack1 status/readyReplicas is 2 during learning run, but 1 during testing run
End state inconsistency - fewer object fields than reference: pod/default/cassandra-test-cluster-dc1-rack1-1 status/containerStatuses/0/state/running seen as {'startedAt': 'SIEVE-IGNORE'} during learning run, but not seen during testing run
```
The bug was found in commit `fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd`.

### [orange-opensource-casskop-342](https://github.com/Orange-OpenSource/casskop/issues/342)
```
python3 reproduce_bugs.py -p casskop-operator -b unobserved-state-1
```
If reproduced, you will find
```
End state inconsistency - more objects than reference: 2 pod seen after learning run ['cassandra-cluster-dc1-rack1-0', 'casskop-operator-546674cfdd-z4gbj'] but 3 pod seen after testing run ['cassandra-cluster-dc1-rack1-0', 'cassandra-cluster-dc1-rack1-1', 'casskop-operator-57f5584bf6-djb4x']
End state inconsistency - more objects than reference: persistentvolumeclaim/data-cassandra-cluster-dc1-rack1-1 is not seen during learning run, but seen during testing run
...
```
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.

### [rabbitmq-cluster-operator-758](https://github.com/rabbitmq/cluster-operator/issues/758)
```
python3 reproduce_bugs.py -p rabbitmq-operator -b unobserved-state-1
```
If reproduced, you will see errors reported by Sieve including:
```
End state inconsistency - fewer objects than reference: 4 pod seen after learning run ['rabbitmq-cluster-server-0', 'rabbitmq-cluster-server-1', 'rabbitmq-cluster-server-2', 'rabbitmq-operator-b7d5945b-vl85f'] but 3 pod seen after testing run ['rabbitmq-cluster-server-0', 'rabbitmq-cluster-server-1', 'rabbitmq-operator-59585b99dd-lsrd4']
End state inconsistency - fewer objects than reference: persistentvolumeclaim/persistence-rabbitmq-cluster-server-2 is seen during learning run, but not seen during testing run
End state inconsistency - object field has a different value: statefulset/default/rabbitmq-cluster-server spec/replicas is 3 during learning run, but 2 during testing run
End state inconsistency - object field has a different value: statefulset/default/rabbitmq-cluster-server status/currentReplicas is 3 during learning run, but 2 during testing run
End state inconsistency - object field has a different value: statefulset/default/rabbitmq-cluster-server status/readyReplicas is 3 during learning run, but 2 during testing run
End state inconsistency - object field has a different value: statefulset/default/rabbitmq-cluster-server status/replicas is 3 during learning run, but 2 during testing run
End state inconsistency - object field has a different value: statefulset/default/rabbitmq-cluster-server status/updatedReplicas is 3 during learning run, but 2 during testing run
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

### [percona-server-mongodb-operator-585](https://jira.percona.com/browse/K8SPSMDB-585)
```
python3 reproduce_bugs.py -p mongodb-operator -b unobserved-state-1
```
If reproduced, you will see errors reported by Sieve including:
```
End state inconsistency - fewer objects than reference: persistentvolumeclaim/mongod-data-mongodb-cluster-rs0-4 is seen during learning run, but not seen during testing run
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

### [yugabyte-operator-39](https://github.com/yugabyte/yugabyte-operator/issues/39)
```
python3 reproduce_bugs.py -p yugabyte-operator -b unobserved-state-1
```
If reproduced, you will see errors reported by Sieve including:
```
End state inconsistency - fewer objects than reference: 8 pod seen after learning run ['yb-master-0', 'yb-master-1', 'yb-master-2', 'yb-tserver-0', 'yb-tserver-1', 'yb-tserver-2', 'yb-tserver-3', 'yugabyte-operator-86f6465d9b-r49zx'] but 7 pod seen after testing run ['yb-master-0', 'yb-master-1', 'yb-master-2', 'yb-tserver-0', 'yb-tserver-1', 'yb-tserver-2', 'yugabyte-operator-577c59b656-8744b']
End state inconsistency - fewer objects than reference: persistentvolumeclaim/datadir0-yb-tserver-3 is seen during learning run, but not seen during testing run
```
This bug was found in commit `966ef1978ed5d714119548b2c4343925fe49f882`.

### [percona-xtradb-cluster-operator-918](https://jira.percona.com/browse/K8SPXC-918)
```
python3 reproduce_bugs.py -p xtradb-operator -b unobserved-state-1
```
If reproduced, you will see errors reported by Sieve including:
```
End state inconsistency - fewer objects than reference: persistentvolumeclaim/datadir-xtradb-cluster-pxc-3 is seen during learning run, but not seen during testing run
End state inconsistency - fewer objects than reference: persistentvolumeclaim/datadir-xtradb-cluster-pxc-4 is seen during learning run, but not seen during testing run
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

### Stale state bugs

<!-- ### [datastax-cass-operator-412](https://github.com/datastax/cass-operator/issues/412) -->
### [k8ssandra-cass-operator-559](https://k8ssandra.atlassian.net/browse/K8SSAND-559)
```
python3 reproduce_bugs.py -p cass-operator -b stale-state-1
```
If reproduced, you will see errors reported by Sieve including:
```
End state inconsistency - more object fields than reference: persistentvolumeclaim/default/server-data-cluster1-cassandra-datacenter-default-sts-0 metadata/deletionTimestamp not seen during learning run, but seen as 2022-01-04T03:49:18Z during testing run
```
The bug was found in commit `dbd4f7a10533bb2298aed0d40ea20bfd8c133da2`.

### [instaclustr-cassandra-operator-402](https://github.com/instaclustr/cassandra-operator/issues/402)
```
python3 reproduce_bugs.py -p cassandra-operator -b stale-state-1
```
If reproduced, you will see errors reported by Sieve including:
```
End state inconsistency - more object fields than reference: persistentvolumeclaim/default/data-volume-cassandra-test-cluster-dc1-rack1-0 metadata/deletionTimestamp not seen during learning run, but seen as 2022-01-04T03:30:36Z during testing run
```
The bug was found in commit `fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd`.

### [instaclustr-cassandra-operator-407](https://github.com/instaclustr/cassandra-operator/issues/407)
```
python3 reproduce_bugs.py -p cassandra-operator -b stale-state-2
```
If reproduced, you will see errors reported by Sieve including:
```
End state inconsistency - more object fields than reference: persistentvolumeclaim/default/data-volume-cassandra-test-cluster-dc1-rack1-1 metadata/deletionTimestamp not seen during learning run, but seen as 2022-01-04T03:40:26Z during testing run
```
The bug was found in commit `bd8077a478997f63862848d66d4912c59e4c46ff`.

### [orange-opensource-casskop-316](https://github.com/Orange-OpenSource/casskop/issues/316)
```
python3 reproduce_bugs.py -p casskop-operator -b stale-state-1
```
If reproduced, you will see errors reported by Sieve including:
```
End state inconsistency - more object fields than reference: persistentvolumeclaim/default/data-cassandra-cluster-dc1-rack1-0 metadata/deletionTimestamp not seen during learning run, but seen as 2022-01-04T03:56:54Z during testing run
```
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.

### [orange-opensource-casskop-321](https://github.com/Orange-OpenSource/casskop/issues/321)
```
python3 reproduce_bugs.py -p casskop-operator -b stale-state-2
```
If reproduced, you will see errors reported by Sieve including:
```
State-update summaries inconsistency: /poddisruptionbudgets/default/cassandra-cluster ADDED inconsistency: 2 events seen during learning run, but 4 seen during testing run
State-update summaries inconsistency: /poddisruptionbudgets/default/cassandra-cluster DELETED inconsistency: 1 events seen during learning run, but 3 seen during testing run
```
The bug was found in commit `f87c8e05c1a2896732fc5f3a174f1eb99e936907`.

### [percona-server-mongodb-operator-430](https://jira.percona.com/browse/K8SPSMDB-430)
```
python3 reproduce_bugs.py -p mongodb-operator -b stale-state-1
```
If reproduced, you will see errors reported by Sieve including:
```
State-update summaries inconsistency: /persistentvolumeclaims/default/mongod-data-mongodb-cluster-rs0-0 ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /persistentvolumeclaims/default/mongod-data-mongodb-cluster-rs0-0 DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /persistentvolumeclaims/default/mongod-data-mongodb-cluster-rs0-1 ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /persistentvolumeclaims/default/mongod-data-mongodb-cluster-rs0-1 DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /persistentvolumeclaims/default/mongod-data-mongodb-cluster-rs0-2 ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /persistentvolumeclaims/default/mongod-data-mongodb-cluster-rs0-2 DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /poddisruptionbudgets/default/mongodb-cluster-mongod-rs0 ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /poddisruptionbudgets/default/mongodb-cluster-mongod-rs0 DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /statefulsets/default/mongodb-cluster-rs0 ADDED inconsistency: 3 events seen during learning run, but 4 seen during testing run
State-update summaries inconsistency: /statefulsets/default/mongodb-cluster-rs0 DELETED inconsistency: 2 events seen during learning run, but 3 seen during testing run
End state inconsistency - object field has a different value: perconaservermongodb/default/mongodb-cluster status/state is ready during learning run, but error during testing run
End state inconsistency - fewer object fields than reference: perconaservermongodb/default/mongodb-cluster status/mongoImage seen as percona/percona-server-mongodb:4.4.3-5 during learning run, but not seen during testing run
End state inconsistency - fewer object fields than reference: perconaservermongodb/default/mongodb-cluster status/mongoVersion seen as 4.4.3-5 during learning run, but not seen during testing run
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

### [percona-server-mongodb-operator-433](https://jira.percona.com/browse/K8SPSMDB-433)
```
python3 reproduce_bugs.py -p mongodb-operator -b stale-state-2
```
If reproduced, you will see errors reported by Sieve including:
```
State-update summaries inconsistency: /poddisruptionbudgets/default/mongodb-cluster-cfg-cfg ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /poddisruptionbudgets/default/mongodb-cluster-cfg-cfg DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /pods/default/mongodb-cluster-cfg-0 ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /pods/default/mongodb-cluster-cfg-0 DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /services/endpoints/default/mongodb-cluster-cfg ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /services/endpoints/default/mongodb-cluster-cfg DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /services/specs/default/mongodb-cluster-cfg ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /services/specs/default/mongodb-cluster-cfg DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /statefulsets/default/mongodb-cluster-cfg ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /statefulsets/default/mongodb-cluster-cfg DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

### [percona-server-mongodb-operator-438](https://jira.percona.com/browse/K8SPSMDB-438)
```
python3 reproduce_bugs.py -p mongodb-operator -b stale-state-3
```
If reproduced, you will see errors reported by Sieve including:
```
State-update summaries inconsistency: /poddisruptionbudgets/default/mongodb-cluster-arbiter-rs0 ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /poddisruptionbudgets/default/mongodb-cluster-arbiter-rs0 DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /pods/default/mongodb-cluster-rs0-4 ADDED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /pods/default/mongodb-cluster-rs0-4 DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /pods/default/mongodb-cluster-rs0-arbiter-0 ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /pods/default/mongodb-cluster-rs0-arbiter-0 DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /statefulsets/default/mongodb-cluster-rs0-arbiter ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /statefulsets/default/mongodb-cluster-rs0-arbiter DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `c12b69e2c41efc67336a890039394250420f60bb`.

### [rabbitmq-cluster-operator-648](https://github.com/rabbitmq/cluster-operator/issues/648)
```
python3 reproduce_bugs.py -p rabbitmq-operator -b stale-state-1
```
If reproduced, you will see errors reported by Sieve including:
```
State-update summaries inconsistency: /pods/default/rabbitmq-cluster-server-0 ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /pods/default/rabbitmq-cluster-server-0 DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /statefulsets/default/rabbitmq-cluster-server ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /statefulsets/default/rabbitmq-cluster-server DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
...
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

### [rabbitmq-cluster-operator-653](https://github.com/rabbitmq/cluster-operator/issues/653)
```
python3 reproduce_bugs.py -p rabbitmq-operator -b stale-state-2
```
If reproduced, you will see errors reported by Sieve including:
```
State-update summaries inconsistency: /statefulsets/default/rabbitmq-cluster-server ADDED inconsistency: 2 events seen during learning run, but 4 seen during testing run
State-update summaries inconsistency: /statefulsets/default/rabbitmq-cluster-server DELETED inconsistency: 1 events seen during learning run, but 3 seen during testing run
```
The bug was found in commit `4f13b9a942ad34fece0171d2174aa0264b10e947`.

### [percona-xtradb-cluster-operator-716](https://jira.percona.com/browse/K8SPXC-716)
```
python3 reproduce_bugs.py -p xtradb-operator -b stale-state-1
```
If reproduced, you will see errors reported by Sieve including:
```
State-update summaries inconsistency: /persistentvolumeclaims/default/datadir-xtradb-cluster-pxc-0 ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /persistentvolumeclaims/default/datadir-xtradb-cluster-pxc-0 DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /persistentvolumeclaims/default/datadir-xtradb-cluster-pxc-1 ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /persistentvolumeclaims/default/datadir-xtradb-cluster-pxc-1 DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /persistentvolumeclaims/default/datadir-xtradb-cluster-pxc-2 ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /persistentvolumeclaims/default/datadir-xtradb-cluster-pxc-2 DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /poddisruptionbudgets/default/xtradb-cluster-pxc ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /poddisruptionbudgets/default/xtradb-cluster-pxc DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /statefulsets/default/xtradb-cluster-pxc ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /statefulsets/default/xtradb-cluster-pxc DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

### [percona-xtradb-cluster-operator-725](https://jira.percona.com/browse/K8SPXC-725)
```
python3 reproduce_bugs.py -p xtradb-operator -b stale-state-2
```
If reproduced, you will see errors reported by Sieve including:
```
State-update summaries inconsistency: /poddisruptionbudgets/default/xtradb-cluster-haproxy ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /poddisruptionbudgets/default/xtradb-cluster-haproxy DELETED inconsistency: 1 events seen during learning run, but 2 seen duri
ng testing run
State-update summaries inconsistency: /pods/default/xtradb-cluster-haproxy-0 ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /pods/default/xtradb-cluster-haproxy-0 DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
...
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

### [percona-xtradb-cluster-operator-763](https://jira.percona.com/browse/K8SPXC-763)
```
python3 reproduce_bugs.py -p xtradb-operator -b stale-state-3
```
If reproduced, you will see errors reported by Sieve including:
```
State-update summaries inconsistency: /persistentvolumeclaims/default/proxydata-xtradb-cluster-proxysql-0 ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /persistentvolumeclaims/default/proxydata-xtradb-cluster-proxysql-0 DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /poddisruptionbudgets/default/xtradb-cluster-proxysql ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /poddisruptionbudgets/default/xtradb-cluster-proxysql DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /pods/default/xtradb-cluster-proxysql-0 ADDED inconsistency: 2 events seen during learning run, but 4 seen during testing run
State-update summaries inconsistency: /pods/default/xtradb-cluster-proxysql-0 DELETED inconsistency: 1 events seen during learning run, but 3 seen during testing run
...
```
The bug was found in commit `29092c9b145af6eaf5cbff534287483bec4167b6`.

### [yugabyte-operator-35](https://github.com/yugabyte/yugabyte-operator/issues/35)
```
python3 reproduce_bugs.py -p yugabyte-operator -b stale-state-1
```
If reproduced, you will see errors reported by Sieve including:
```
State-update summaries inconsistency: /secrets/default/yb-master-yugabyte-tls-cert ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /secrets/default/yb-master-yugabyte-tls-cert DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /secrets/default/yb-tserver-yugabyte-tls-cert ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /secrets/default/yb-tserver-yugabyte-tls-cert DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
...
```
This bug was found in commit `966ef1978ed5d714119548b2c4343925fe49f882`.

### [yugabyte-operator-36](https://github.com/yugabyte/yugabyte-operator/issues/36)
```
python3 reproduce_bugs.py -p yugabyte-operator -b stale-state-2
```
If reproduced, you will see errors reported by Sieve including:
```
State-update summaries inconsistency: /services/endpoints/default/yb-tserver-ui ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /services/endpoints/default/yb-tserver-ui DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /services/specs/default/yb-tserver-ui ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /services/specs/default/yb-tserver-ui DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
This bug was found in commit `966ef1978ed5d714119548b2c4343925fe49f882` with the prerequisite 
[fix](https://github.com/yugabyte/yugabyte-operator/pull/34).

### [pravega-zookeeper-operator-312](https://github.com/pravega/zookeeper-operator/issues/312)
```
python3 reproduce_bugs.py -p zookeeper-operator -b stale-state-1
```
If reproduced, you will see errors reported by Sieve including:
```
End state inconsistency - more object fields than reference: persistentvolumeclaim/default/data-zookeeper-cluster-0 metadata/deletionTimestamp not seen during learning run, but seen as 2022-01-04T05:26:36Z during testing run
```
The bug was found in commit `cda03d2f270bdfb51372192766123904f6d88278`.

### [pravega-zookeeper-operator-314](https://github.com/pravega/zookeeper-operator/issues/314)
```
python3 reproduce_bugs.py -p zookeeper-operator -b stale-state-2
```
If reproduced, you will see errors reported by Sieve including:
```
State-update summaries inconsistency: /persistentvolumeclaims/default/data-zookeeper-cluster-1 ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /persistentvolumeclaims/default/data-zookeeper-cluster-1 DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
State-update summaries inconsistency: /pods/default/zookeeper-cluster-1 ADDED inconsistency: 2 events seen during learning run, but 3 seen during testing run
State-update summaries inconsistency: /pods/default/zookeeper-cluster-1 DELETED inconsistency: 1 events seen during learning run, but 2 seen during testing run
```
The bug was found in commit `cda03d2f270bdfb51372192766123904f6d88278`.

### Indirect bugs
Note that Sieve does NOT guarantee to reliably reproduce the following indirect bugs as these bugs are not directly triggered by the test plans generated by our Sieve.

### [instaclustr-cassandra-operator-400](https://github.com/instaclustr/cassandra-operator/issues/400)
```
python3 reproduce_bugs.py -p cassandra-operator -b indirect-1
```
If reproduced, you will see errors reported by Sieve including:
```
Error from the workload: error: hard timeout: cassandra-test-cluster-dc1-rack1-1 does not become Terminated within 600 seconds
```

### [instaclustr-cassandra-operator-410](https://github.com/instaclustr/cassandra-operator/issues/410)
```
python3 reproduce_bugs.py -p cassandra-operator -b indirect-2
```
If reproduced, you will see errors reported by Sieve including:
```
End state inconsistency - object field has a different value: pod/default/cassandra-test-cluster-dc1-rack1-1["status"]["containerStatuses"][0]["ready"] is True after reference run, but False after testing run
End state inconsistency - object field has a different value: statefulset/default/cassandra-test-cluster-dc1-rack1["status"]["readyReplicas"] is 2 after reference run, but 1 after testing run
```

### [percona-server-mongodb-operator-434](https://jira.percona.com/browse/K8SPSMDB-434)
```
python3 reproduce_bugs.py -p mongodb-operator -b indirect-1
```
If reproduced, you will see errors reported by Sieve including:
```
Exception from controller: Observed a panic: "invalid memory address or nil pointer dereference" (runtime error: invalid memory address or nil pointer dereference)
```

### [percona-server-mongodb-operator-590](https://jira.percona.com/browse/K8SPSMDB-590)
```
python3 reproduce_bugs.py -p mongodb-operator -b indirect-2
```
If reproduced, you will see errors reported by Sieve including:
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

### [percona-server-mongodb-operator-591](https://jira.percona.com/browse/K8SPSMDB-591)
```
python3 reproduce_bugs.py -p mongodb-operator -b indirect-3
```
If reproduced, you will see errors reported by Sieve including:
```
End state inconsistency - object field has a different value: perconaservermongodb/default/mongodb-cluster["status"]["state"] is ready after learning run, but error after testing run
End state inconsistency - fewer object fields than reference: perconaservermongodb/default/mongodb-cluster["status"]["replsets"]["rs0"]["added_as_shard"] is True after learning run, but not seen after testing run
```

### [yugabyte-operator-33](https://github.com/yugabyte/yugabyte-operator/issues/33)
```
python3 reproduce_bugs.py -p yugabyte-operator -b indirect-1
```
If reproduced, you will see errors reported by Sieve including:
```
Error from the workload: error: cmd 'kubectl patch YBCluster example-ybcluster --type merge -p='{"spec":{"tserver":{"tserverUIPort": 0}}}'' return non-zero code 1
Error from the workload: error: hard timeout: yb-tserver-ui does not become non-exist within 600 seconds
```

### [yugabyte-operator-43](https://github.com/yugabyte/yugabyte-operator/issues/43)
```
python3 reproduce_bugs.py -p yugabyte-operator -b indirect-2
```
If reproduced, you will see errors reported by Sieve including:
```
End state inconsistency - object field has a different value: pod/default/yb-master-2["status"]["containerStatuses"][0]["state"]["runni$g"] is {'StartedAt': '2022-02-04T08:50:21Z'} after reference run, but None after testing run
```

### [zookeeper-operator-410](https://github.com/pravega/zookeeper-operator/issues/410)
```
python3 reproduce_bugs.py -p zookeeper-operator -b indirect-1
```
If reproduced, you will see errors reported by Sieve including:
```
State-update summaries inconsistency: configmap/default/zookeeper-cluster-configmap ADDED inconsistency: 2 event(s) seen during referenc
e run, but 3 seen during testing run                                                                                                    
State-update summaries inconsistency: configmap/default/zookeeper-cluster-configmap DELETED inconsistency: 1 event(s) seen during refere
nce run, but 2 seen during testing run
```
