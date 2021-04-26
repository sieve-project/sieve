## Using Sonar to detect a time-travel bug in rabbitmq-operator

### What is Sonar?

Sonar is a bug detection tool for finding bugs in kubernetes controllers.
One of the bug patterns Sonar targets is a time-travel bug, i.e., bugs caused by a controller "going back in time" after restarts.

### What is a time-travel bug?

Time-travel bugs happen when the controller reads stale cluster state from a *stale* apiserver and behaves unexpectedly. Consider the following scenario:

<img src="time-travel.png" width="80%">

1. In a HA kubernetes cluster, the controller is connecting to apiserver1. Initially each apiserver is updated with the current cluster state `S1`, and the controller performs reconciliation according to the state read from apiserver1.

2. Now apiserver2's locally cached status gets updated by etcd to `S2`, while apiserver2's does not get updated in time and still holds the stale state `S1` (due to various reasons like apiserver2 being slow, experiencing a network disruption or temporary resouce contention).

3. The controller restarts after experiencing a node failure and connects to apiserver2. The controller reads stale `S1` and performs reconciliation accordingly. The reconciliation triggered by reading `S1` again may lead to some unexpected behavior and cause failures like data loss or service unavailability.


### How does Sonar work (at a high level)?
To detect time-travel bugs, Sonar will create the above time travel scenario in a [kind cluster](https://kind.sigs.k8s.io/) to trigger the bug. In other words, Sonar performs failure testing by pausing the apiserver and restarting the controller at certain timing to make the controller experience time travel.

The following explains how Sonar detects a time-travel bug in [rabbitmq-operator](https://github.com/rabbitmq/cluster-operator).

### Prerequisite
**Kind cluster is required**. Sonar tests the controller in a kind cluster, so kind needs to be installed for testing.

**The controller needs to be recompiled**. Some porting effort is required to use Sonar to test any controller.
We have already ported [rabbitmq-operator](https://github.com/rabbitmq/cluster-operator) (as in https://github.com/xlab-uiuc/sonar/tree/main/test-rabbitmq-operator) and rebuilt the images.

### Testing the controller with time travel config
Now, let's test the rabbitmq-operator
```
python3 run.py -p rabbitmq-operator -t test1 -c log/rabbitmq-operator/test1/learn/generated-config/time-travel-1.yaml
```
`test1` is the test workload (written by us) that Sonar will run.
The workload simply does three things:
1. it creates a rabbitmq cluster `kubectl apply -f rmqc-1.yaml`
2. it deletes the rabbitmq cluster `kubectl delete RabbitmqCluster rabbitmq-cluster`
3. it recreates the rabbitmq cluster `kubectl apply -f rmqc-1.yaml`

`log/rabbitmq-operator/test1/learn/generated-config/time-travel-1.yaml` is a configuration file which guides the failure testing (for example, the schedule for restarting controllers or lagging apiservers). We will later explain how this configuration file is generated.

By typing the above command, Sonar will:
1. run the `test1` workload against the kind kubernetes cluster;
2. create the time-travel scenario during the test run according to the configuration file, `time-travel-1.yaml`.

When it finishes, you will see a bug is detected by Sonar that:
```
[CHECKING] side effect
[ERROR] statefulset/default/rabbitmq-cluster-server Create inconsistency: normal: 2, testing: 3
[ERROR] statefulset/default/rabbitmq-cluster-server Delete inconsistency: normal: 1, testing: 2
[BUG REPORT] # alarms: 2
[TIME TRAVEL DESC] Sonar makes the controller time travel back to the history to see the status just after rabbitmqcluster/default/rabbitmq-cluster: {"metadata": {"deletionTimestamp": "SONAR-NON-NIL", "deletionGracePeriodSeconds": 0}} (at kind-control-plane3)
[DEBUG SUGGESTION] Please check how controller reacts when seeing rabbitmqcluster/default/rabbitmq-cluster: {"metadata": {"deletionTimestamp": "SONAR-NON-NIL", "deletionGracePeriodSeconds": 0}}, the controller may issue deletion to statefulset/default/rabbitmq-cluster-server without proper checking
```
Sonar generates a bug report saying that the controller issues more `CREATE` and `DELETE` operations for the resource named `statefulset/default/sonar-rabbitmq-cluster-server` than normal. It suggests that this inconsistency is probably caused by the controller issuing deletions without proper checking when seeing the non-nil `deletionTimestamp` of the resource named `rabbitmqcluster/default/sonar-rabbitmq-cluster`.

### Debugging with Sonar report
Sonar gives us a hint about the bug, but cannot automatically tell us the root cause. Debugging still requires some manual effort. Here is my experience:

I searched `deletionTimestamp` in the controller code to see how the controller reacts to it and I found:
```go
	// Check if the resource has been marked for deletion
	if !rabbitmqCluster.ObjectMeta.DeletionTimestamp.IsZero() {
		logger.Info("Deleting")
		return ctrl.Result{}, r.prepareForDeletion(ctx, rabbitmqCluster)
	}
```
The controller tries to delete the statefulset when seeing non-nil `deletionTimestamp` without checking the ownership of the statefulset.

Combining the `TIME TRAVEL DESC` and the `DEBUG SUGGESTION` from Sonar, the bug is identified:
After the rabbitmq cluster gets recreated by `test1`, Sonar makes the controller time travel back to see the non-nil `deletionTimestamp` (caused by the previous rabbitmq cluster deletion). Since the controller does not check statefuset ownership `prepareForDeletion`, it immediately deletes the currently running statefulset as a reaction of seeing the stale `deletionTimestamp`.

The detected bug is filed at https://github.com/rabbitmq/cluster-operator/issues/648 and has been fixed.

### What is in the time travel config?

Recall that we need to pause the apiserver and restart the controller with **a certain timing**. The time travel configuration file specifies the required timing for pausing the apiservers or restarting the controller.

Let's look into the generated time-travel config `log/rabbitmq-operator/test1/learn/generated-config/time-travel-1.yaml`:
```
project: rabbitmq-operator
mode: time-travel
straggler: kind-control-plane3
front-runner: kind-control-plane
operator-pod-label: rabbitmq-operator
deployment-name: rabbitmq-operator
timing: after
ce-name: rabbitmq-cluster
ce-namespace: default
ce-rtype: rabbitmqcluster
ce-diff-current: '{"metadata": {"deletionTimestamp": "SONAR-NON-NIL", "deletionGracePeriodSeconds": 0}}'
ce-diff-previous: '{}'
ce-etype-current: Updated
ce-etype-previous: Updated
se-name: rabbitmq-cluster-server
se-namespace: default
se-rtype: statefulset
se-etype: ADDED
description: 'Pause kind-control-plane3 after it processes a default/rabbitmqcluster/rabbitmq-cluster
  event E. E should match the pattern {"metadata": {"deletionTimestamp": "SONAR-NON-NIL",
  "deletionGracePeriodSeconds": 0}} and the events before E should match {}. And restart
  the controller rabbitmq-operator after kind-control-plane processes a ADDED default/statefulset/rabbitmq-cluster-server
  event.'
```
It looks a little bit complicated here. But don't worry. For now, you only need to understand a few fields here.

First,
```
straggler: kind-control-plane3
front-runner: kind-control-plane
```
means during testing we want to pause apiserver3 (which runs on `kind-control-plane3`) at **certain timing** to create the stale status.
And we use apiserver1 (which runs on `kind-control-plane`) as a referrence to restart the controller at **certain timing**.
The difficult part is how to decide the **timing** here.

Now let's look at
```
ce-name: rabbitmq-cluster
ce-namespace: default
ce-rtype: rabbitmqcluster
ce-diff-current: '{"metadata": {"deletionTimestamp": "SONAR-NON-NIL", "deletionGracePeriodSeconds": 0}}'
ce-diff-previous: '{}'
```
This is how Sonar decides when to pause the apiserver3. When Sonar sees an event belonging to `rabbitmqcluster/default/rabbitmq-cluster` and contains the sub-map in `ce-diff-current`, and a previous event contains the sub-map in `ce-diff-previous`,
Sonar will pause the apiserver3. Here, `ce-diff-current` basically means the event sets a `deletionTimestamp`, and `ce-diff-previous` does not pose any constraint since it is empty.

Finally, Sonar needs to decide when to restart the controller
```
se-name: rabbitmq-cluster-server
se-namespace: default
se-rtype: statefulset
se-etype: ADDED
```
When Sonar sees an `ADDED` event belonging to `statefulset/default/rabbitmq-cluster-server`, it will restart the controller and connect the controller to the paused apiserver3.

You will also find the explanation from the `description` field.


### How is the time travel config generated?
The biggest challenge to generate the above time travel config is to find out the appropriate timing for injecting pause/restart.

Sonar has a `learn` mode to infer the causality between events triggering `reconcile()` and side effects (resource creation/update/deletion) issued during `reconcile()`,
and Sonar then picks each potentially causal-related <event, side effect> pair to decide the timing. 

To do so, run:
```
python3 run.py -p rabbitmq-operator -t test1 -m learn
```
The command will run test workload `test1` in Sonar `learn` mode, collect the events and side effects, infer the causality and generate the promising timing to for pausing apiserver/restarting controller.

After it finishes, you will see
```
Generated 1 time-travel config(s) in log/rabbitmq-operator/test1/learn/generated-config
```

The generated config is exactly the one shown before.
