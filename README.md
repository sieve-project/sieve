# Sonar: Testing Partial History Bugs

## Bugs Found:
[instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398) confirmed and fixed by our patch

[instaclustr-cassandra-operator-400](https://github.com/instaclustr/cassandra-operator/issues/400) confirmed and fixed by our patch

[instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/402) confirmed and fixed by our patch

[instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/404) confirmed and fixed by our patch

## Reproduction:
**Requirement: go1.13 installed and `$GOPATH` set**

### [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398):
First,
```
./build.sh
```
This will download Kubernetes-v1.18.9 into `fakegopath` directory and build kind image.

Second,
```
cd cassandra-operator
./install.sh
```
This will download https://github.com/instaclustr/cassandra-operator (fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd) into `app`, run necessary instrumentation on the source code (injecting callsites to sonar client lib API), and build the docker image for later use.

Last,
```
./workload1.sh
```
This will run the workload to reproduce the bug. System states and other logs can be found at `log` directory.
To verify the bug is exposed, `log/stdout.log` will show:
```
>>> before scale down:
NAME                                  READY   STATUS    RESTARTS   AGE     IP           NODE           NOMINATED NODE   READINESS GATES
cassandra-operator-7fcbcc999c-6tp4q   1/1     Running   0          4m24s   10.244.1.2   kind-worker    <none>           <none>
cassandra-test-cluster-dc1-rack1-0    2/2     Running   0          3m10s   10.244.2.3   kind-worker2   <none>           <none>
cassandra-test-cluster-dc1-rack1-1    2/2     Running   0          102s    10.244.1.4   kind-worker    <none>           <none>
NAME                                             STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE     VOLUMEMODE
data-volume-cassandra-test-cluster-dc1-rack1-0   Bound    pvc-1f158d58-df29-4b63-82fe-dda8aba7d8f2   2Gi        RWO            standard       3m10s   Filesystem
data-volume-cassandra-test-cluster-dc1-rack1-1   Bound    pvc-7f04f2a6-c6cc-431a-ac75-5c1e7dc456b6   2Gi        RWO            standard       102s    Filesystem
>>> after scale down:
NAME                                  READY   STATUS    RESTARTS   AGE     IP           NODE           NOMINATED NODE   READINESS GATES
cassandra-operator-7fcbcc999c-6tp4q   1/1     Running   0          6m55s   10.244.1.2   kind-worker    <none>           <none>
cassandra-test-cluster-dc1-rack1-0    2/2     Running   0          5m41s   10.244.2.3   kind-worker2   <none>           <none>
NAME                                             STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE     VOLUMEMODE
data-volume-cassandra-test-cluster-dc1-rack1-0   Bound    pvc-1f158d58-df29-4b63-82fe-dda8aba7d8f2   2Gi        RWO            standard       5m41s   Filesystem
data-volume-cassandra-test-cluster-dc1-rack1-1   Bound    pvc-7f04f2a6-c6cc-431a-ac75-5c1e7dc456b6   2Gi        RWO            standard       4m13s   Filesystem
```
As shown above, after scale-down there is only one cassandra pod (`cassandra-test-cluster-dc1-rack1-0`) but there are still two PVCs.

### [instaclustr-cassandra-operator-400](https://github.com/instaclustr/cassandra-operator/issues/400):
This one is not a partial history bug and can also be reproduced by `./workload1.sh` with the above steps.
To verify, `log/stdout.log` will show:
```
>>> before scale down:
NAME                                  READY   STATUS    RESTARTS   AGE     IP           NODE           NOMINATED NODE   READINESS GATES
cassandra-operator-7fcbcc999c-lzs6r   1/1     Running   0          4m23s   10.244.1.2   kind-worker    <none>           <none>
cassandra-test-cluster-dc1-rack1-0    2/2     Running   0          3m10s   10.244.2.3   kind-worker2   <none>           <none>
cassandra-test-cluster-dc1-rack1-1    2/2     Running   0          104s    10.244.1.4   kind-worker    <none>           <none>
NAME                                             STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE     VOLUMEMODE
data-volume-cassandra-test-cluster-dc1-rack1-0   Bound    pvc-70af44fb-c7b9-44f6-bea3-ef74691d5bf9   2Gi        RWO            standard       3m10s   Filesystem
data-volume-cassandra-test-cluster-dc1-rack1-1   Bound    pvc-392e0fa0-45b3-4881-8809-8095dbb1b548   2Gi        RWO            standard       104s    Filesystem
>>> after scale down:
NAME                                  READY   STATUS    RESTARTS   AGE     IP           NODE           NOMINATED NODE   READINESS GATES
cassandra-operator-7fcbcc999c-lzs6r   1/1     Running   0          6m53s   10.244.1.2   kind-worker    <none>           <none>
cassandra-test-cluster-dc1-rack1-0    1/2     Running   0          5m40s   10.244.2.3   kind-worker2   <none>           <none>
cassandra-test-cluster-dc1-rack1-1    2/2     Running   0          4m14s   10.244.1.4   kind-worker    <none>           <none>
NAME                                             STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE     VOLUMEMODE
data-volume-cassandra-test-cluster-dc1-rack1-0   Bound    pvc-70af44fb-c7b9-44f6-bea3-ef74691d5bf9   2Gi        RWO            standard       5m40s   Filesystem
data-volume-cassandra-test-cluster-dc1-rack1-1   Bound    pvc-392e0fa0-45b3-4881-8809-8095dbb1b548   2Gi        RWO            standard       4m14s   Filesystem
```
As shown above, during scale-down `cassandra-test-cluster-dc1-rack1-0` is wrongly chosen to delete which eventually makes the scale-down fail (`cassandra-test-cluster-dc1-rack1-0` gets stuck in a "half-dead" state).

### [instaclustr-cassandra-operator-402](https://github.com/instaclustr/cassandra-operator/issues/402):
First,
```
./build.sh instr
```
We need to instrument the Kubernetes source code for this bug so passing `instr` argument.

Second,
```
cd cassandra-operator
./install.sh
```
Same as before.

Last,
```
./workload2.sh
```
To verify, `log/stdout.log` will show:
```
>>> after create cdc:
NAME                                  READY   STATUS    RESTARTS   AGE     IP           NODE           NOMINATED NODE   READINESS GATES
cassandra-operator-7fcbcc999c-kp6ld   1/1     Running   0          3m44s   10.244.2.2   kind-worker    <none>           <none>
cassandra-test-cluster-dc1-rack1-0    2/2     Running   0          2m30s   10.244.3.3   kind-worker2   <none>           <none>
NAME                                             STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE     VOLUMEMODE
data-volume-cassandra-test-cluster-dc1-rack1-0   Bound    pvc-27bbe826-21bd-44bf-b085-3dee71b695b9   2Gi        RWO            standard       2m30s   Filesystem
 
>>> after delete cdc:
NAME                                  READY   STATUS    RESTARTS   AGE     IP           NODE          NOMINATED NODE   READINESS GATES
cassandra-operator-7fcbcc999c-kp6ld   1/1     Running   0          4m35s   10.244.2.2   kind-worker   <none>           <none>
 
>>> after create cdc again:
NAME                                  READY   STATUS    RESTARTS   AGE     IP           NODE           NOMINATED NODE   READINESS GATES
cassandra-operator-7fcbcc999c-kp6ld   1/1     Running   0          7m5s    10.244.2.2   kind-worker    <none>           <none>
cassandra-test-cluster-dc1-rack1-0    2/2     Running   0          2m30s   10.244.3.6   kind-worker2   <none>           <none>
NAME                                             STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE     VOLUMEMODE
data-volume-cassandra-test-cluster-dc1-rack1-0   Bound    pvc-ca4849e7-ac01-4acb-802d-5f4013a4bacb   2Gi        RWO            standard       2m30s   Filesystem
 
>>> after restart controller and bind to apiserver2:
NAME                                  READY   STATUS    RESTARTS   AGE     IP           NODE           NOMINATED NODE   READINESS GATES
cassandra-operator-7fcbcc999c-kp6ld   1/1     Running   0          7m35s   10.244.2.2   kind-worker    <none>           <none>
cassandra-test-cluster-dc1-rack1-0    2/2     Running   0          3m      10.244.3.6   kind-worker2   <none>           <none>
NAME                                             STATUS        VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE   VOLUMEMODE
data-volume-cassandra-test-cluster-dc1-rack1-0   Terminating   pvc-ca4849e7-ac01-4acb-802d-5f4013a4bacb   2Gi        RWO            standard       3m    Filesystem
```
As shown above, after restarting the controller the PVC `data-volume-cassandra-test-cluster-dc1-rack1-0` will be deleted and get stuck in `Terminating` state.

### [instaclustr-cassandra-operator-404](https://github.com/instaclustr/cassandra-operator/issues/404):
Work in progress...


## Notes:
1. reproduction scripts run typicall slow (may take several minutes to finish one run) because I intentionally add some sleep in the scripts to make sure the controller can finish its job and goes back to stable state before we manipulate its partial history. Sometimes it takes quite long time for a controller to start/delete a pod so the sleep is set to long.
2. There is no explicit oracle to detect the bug for now and we rely on reading the `log/stdout.log` to verify the bug is reproduced. **This is a TODO that I will try to implement oracles using metamorphic testing.**
3. `./workload1.sh` may not always reproduce [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398) because the policy used does not manipulate the timing very well. Currently the bug can be successfully reproduced in more than 90% cases. If not see the expected output, just run it again. **This is a TODO that I will implement a new policy to 100% reproduce [instaclustr-cassandra-operator-398](https://github.com/instaclustr/cassandra-operator/issues/398) every time.**
4. `./workload1.sh` may not always reproduce [instaclustr-cassandra-operator-400](https://github.com/instaclustr/cassandra-operator/issues/400) as well because this bug is caused by some random-indexed data structure (`map`) and it is actually a side-product. Since it is not a partial history bug and we have no plan on random-indexed data structures, it should be fine that it cannot be 100% reproduced every time.
5. Some reproduction requires restarting the controller. However, currently the crashing and restarting is done by the workload scripts instead of the sonar server. **This is a TODO that I will implement the mechanism to make the sonar server able to inject crash.**
