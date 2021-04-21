## Using Sonar to detect a time-travel bug in rabbitmq-operator

### What is Sonar?

Sonar is a bug detection tool for finding partial-history bugs in kubernetes controllers. There are multiple partial-history bug patterns. This demo will mainly focus on finding paritial history bugs caused by time traveling behavior (i.e., time-travel bugs).

### What is a time-travel bug?

Time-travel bugs happen when the controller reads stale cluster status from a stale apiserver and behaves unexpectedly. Consider the following scenario:

In a HA (mulitple apiservers) kubernetes cluster, the controller is connecting to apiserver1. Initially each apiserver is updated with the current cluster status `S1`, and the controller performs reconciliation according to the state read from apiserver1.

<img src="time-travel-1.png" width="300">

Now some network disruption isolates apiserver2 from the underlying etcd, and apisever2 will not be able to get updated by etcd. Apisever1 is not affected, and its locally cached cluster status gets updated to `S2`.

<img src="time-travel-2.png" width="300">

The controller restarts after experiencing a node failure and connects to apiserver2. The isolated apiserver2 still holds the stale view `S1` though the actual status should be `S2`. The controller will read `S1` and perform reconciliation accordingly. The reconciliation triggered by reading `S1` again may lead to some unexpected behavior and cause failures like data loss or service unavailability.

<img src="time-travel-3.png" width="300">

### How does Sonar work (at a high level)?
To detect time-travel bugs, Sonar will create the above time travel scenario in a [kind](https://kind.sigs.k8s.io/) cluster to trigger the bugs.
The key challenge is to find out the appropriate "harmful" status `S` that can lead to bugs when consumed by the controller.
The following explains how Sonar detects a time-travel bug in [rabbitmq-operator](https://github.com/rabbitmq/cluster-operator).

### Prerequisite
Some porting effort is required to use Sonar to test any controller.
The detailed steps are in https://github.com/xlab-uiuc/sonar/blob/main/docs/port.md.
We have already ported [rabbitmq-operator](https://github.com/rabbitmq/cluster-operator) (as in https://github.com/xlab-uiuc/sonar/tree/main/test-rabbitmq-operator).

Before testing, we need to build the kubernetes and rabbitmq-operator images:
```
python3 build.py -p kubernetes -m learn
python3 build.py -p rabbitmq-operator -m learn
python3 build.py -p kubernetes -m time-travel
python3 build.py -p rabbitmq-operator -m time-travel
```

### Finding the "harmful" status to trigger bugs
Not every stale status `S` will lead to bugs in reality. Sonar finds out the stale status `S` which is more likely to lead to bugs if consumed by the controller.
In kubernetes, all the cluster status is materialized by events belonging to different resources.
The first step is to find out the crucial event `E` which can lead to such a "harmful" status `S`.

We define an event `E` is crucial if it can trigger some side effects (resource creation/update/deletion) invoked by the controller.
Sonar has a `learn` mode to infer the causality between events and side effects,
and Sonar then picks each potentially causal-related <crucial event, side effect> pair to guide the testing.

To do so, run:
```
python3 run.py -p rabbitmq-operator -t test1 -m learn
```
The command may take a few minutes to finish. It will run test workload `test1` in Sonar `learn` mode.
`test1` is a simple test workload written by us that creates, deletes and recreates the rabbitmq cluster.
After it finishes, you will see
```
Generated 1 time-travel config(s) in log/rabbitmq-operator/test1/learn/generated-config
```

The config contains many details about when to inject pause and node failure to make the controller go back to history.
We will look into the details later.

### Testing the controller with time travel config
Now, let's test rabbitmq-operator with the generated time-travel config.
```
python3 run.py -p rabbitmq-operator -t test1 -c log/rabbitmq-operator/test1/learn/generated-config/time-travel-1.yaml
```
By typing the command, Sonar will:
1. run a very simple test workload which creates, deletes, and then recreates a rabbitmq cluster in the kind kubernetes cluster;
2. meanwhile, Sonar will create the time-travel scenario during the test run according to the generated time-travel config.

When it finishes, you will see a bug is detected by Sonar that:
```
[BUG REPORT] side effect
[ERROR] statefulset/default/sonar-rabbitmq-cluster-server Create inconsistency: learning: 2, testing: 3
[ERROR] statefulset/default/sonar-rabbitmq-cluster-server Delete inconsistency: learning: 1, testing: 2
[BUGGY] # alarms: 2
```
Sonar detects that the controller mistakenly deletes a statefulset during the test.
The detected bug is filed at https://github.com/rabbitmq/cluster-operator/issues/648 and has been fixed.

### What happened during the test?

Let's look into the generated time-travel config `log/rabbitmq-operator/test1/learn/generated-config/time-travel-1.yaml`:
```
project: rabbitmq-operator
mode: time-travel
straggler: kind-control-plane3
front-runner: kind-control-plane
operator-pod: rabbitmq-operator
command: /manager
timing: after
ce-name: sonar-rabbitmq-cluster
ce-namespace: default
ce-rtype: rabbitmqcluster
ce-diff-current: '{"metadata": {"deletionTimestamp": "SONAR-EXIST", "deletionGracePeriodSeconds": 0}}'
ce-diff-previous: '{}'
ce-etype-current: Updated
ce-etype-previous: Updated
se-name: sonar-rabbitmq-cluster-server
se-namespace: default
se-rtype: statefulset
se-etype: ADDED
description: 'Pause kind-control-plane3 after it processes a default/rabbitmqcluster/sonar-rabbitmq-cluster
  event E. E should match the pattern {"metadata": {"deletionTimestamp": "SONAR-EXIST",
  "deletionGracePeriodSeconds": 0}} and the events before E should match {}. And restart
  the controller rabbitmq-operator after kind-control-plane processes a ADDED default/statefulset/sonar-rabbitmq-cluster-server
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
ce-name: sonar-rabbitmq-cluster
ce-namespace: default
ce-rtype: rabbitmqcluster
ce-diff-current: '{"metadata": {"deletionTimestamp": "SONAR-EXIST", "deletionGracePeriodSeconds": 0}}'
ce-diff-previous: '{}'
```
This is how Sonar decides when to pause the apiserver3. When Sonar sees an event belonging to `rabbitmqcluster/default/sonar-rabbitmq-cluster` and contains the sub-map in `ce-diff-current`, and a previous event contains the sub-map in `ce-diff-previous`,
Sonar will pause the apiserver3. Here, `ce-diff-current` basically means the event sets a `deletionTimestamp`, and `ce-diff-previous` does not pose any constraint since it is empty.

Finally, Sonar needs to decide when to restart the controller
```
se-name: sonar-rabbitmq-cluster-server
se-namespace: default
se-rtype: statefulset
se-etype: ADDED
```
When Sonar sees an `ADDED` event belonging to `statefulset/default/sonar-rabbitmq-cluster-server`, it will restart the controller and connect the controller to the paused apiserver3.

You will also find the explanation from the `description` field. By pausing apiserver3 and restarting controller at the timing above, the controller will behave incorrectly and the unexpected behavior (delete statefulset) gets captured by Sonar as a bug report.
