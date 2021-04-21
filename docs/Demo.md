## Demo: Using sonar to detect a time-travel bug in rabbitmq-operator

### Prerequiste
There is some porting effort required before using sonar to test any controller.
The detailed steps are in https://github.com/xlab-uiuc/sonar/blob/main/docs/Porting.md.
For [rabbitmq-operator](https://github.com/rabbitmq/cluster-operator), we have already done the porting work (as in https://github.com/xlab-uiuc/sonar/tree/main/test-rabbitmq-operator) so no extra porting is required to test it.

### What is time-travel bug?

<img src="time-travel-1.png" width="100">

<img src="time-travel-2.png" width="100">

<img src="time-travel-3.png" width="100">

### Finding the crucial event
Time-travel bugs has the pattern that the controller will perform some unexpected side effects
if certain events are replayed (by sonar) to the controller.
So the first step to detect time travel bug is to find out the (potential) crucial event.
Sonar has a `learn` mode to infer the causality between events and side effects,
and sonar will pick each potentially causal-related <crucial event, side effect> pair to guide the testing.

To do so, run:
```
python3 run.py -p rabbitmq-operator -t test1 -m learn
```
The command may take a few minutes to finish. It will run test workload `test1` in sonar `learn` mode.
`test1` is a simple test workload written by us that creates, deletes and recreates the rabbitmq cluster.
After it finishes, you will see
```
Generated 1 time-travel config(s) in log/rabbitmq-operator/test1/learn/generated-config
```

The config contains many details about when to inject pause and node failure to make the controller go back to history.
We will look into the details later.

### Testing the controller with time travel config
Now let's first test rabbitmq-operator with the generated time travel config.
```
python3 run.py -p rabbitmq-operator -t test1 -c log/rabbitmq-operator/test1/learn/generated-config/time-travel-1.yaml
```
When it finishes, you will see a bug is detected by sonar that:
```
[BUG REPORT] side effect
[ERROR] statefulset.create inconsistent: learning: 2, testing: 3
[ERROR] statefulset.delete inconsistent: learning: 1, testing: 2
[BUG REPORT] status
[ERROR] pod.size inconsistent: learning: 2, testing: 1
[BUGGY] # alarms: 3
```
Sonar detects that the controller mistakenly deletes a statefulset during testing.
The detected bug is filed at https://github.com/rabbitmq/cluster-operator/issues/648 and gets fixed using our patch.

### What happened during the testing?

Now we can look into the generated time travel config `log/rabbitmq-operator/test1/learn/generated-config/time-travel-1.yaml`:
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
ce-diff-current: '{"metadata": {"deletionTimestamp": "SONAR-EXIST", "deletionGracePeriodSeconds":
  0}}'
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
means during testing we want to pause apiserver3 (which runs on `kind-control-plane3`) at **certain timing** to create the stale value.
And we use apiserver1 (which runs on `kind-control-plane`) as a referrence to restart the controller at **certain timing**.
The difficult part is how to decide the **timing** here.

Now let's look at
```
ce-name: sonar-rabbitmq-cluster
ce-namespace: default
ce-rtype: rabbitmqcluster
ce-diff-current: '{"metadata": {"deletionTimestamp": "SONAR-EXIST", "deletionGracePeriodSeconds":
  0}}'
ce-diff-previous: '{}'
```
This is how sonar decides when to pause the apiserver3. When sonar sees an event belonging to `rabbitmqcluster/default/sonar-rabbitmq-cluster` and contains the sub-map in `ce-diff-current`, and a previous event contains the sub-map in `ce-diff-previous`,
sonar will pause the apiserver3. Here, `ce-diff-current` basically means the event sets a `deletionTimestamp`, and `ce-diff-previous` does not pose any constraint since it is empty.

Finally, sonar needs to decide when to restart the controller
```
se-name: sonar-rabbitmq-cluster-server
se-namespace: default
se-rtype: statefulset
se-etype: ADDED
```
When sonar sees an `ADDED` event belonging to `statefulset/default/sonar-rabbitmq-cluster-server`, it will restart the controller and connect the controller to the paused apiserver3.

You will also find the explanation from the `description` field. By pausing apiserver3 and restarting controller at the timing above, the controller will behave incorrectly and the unexpected behavior (delete statefulset) gets captured by sonar as a bug report.
