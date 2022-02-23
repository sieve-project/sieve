# Decouple perturbation policy and mechanism

Xudong Sun

## Overview
This feature aims to fully decouple the perturbation policy and mechanism. That is, users should be able to generate/write test plans (following certain format) to conduct various types of perturbations beyond the three patterns currently supported by Sieve.

Each test plan should consist of a list of actions and each action represent one single fault to inject (e.g., pause the controller), or a recovery from the fault (e.g., resume the controller). Each action is only triggered upon certain triggering conditions defined in the test plan (e.g., on a particular state change).

The test coordinator runs as a state machine defined by the test plan. In the initial state, no single fault is injected and the coordinator watches for any related upcoming events (e.g., resource creation, update, deletion) and checks whether the triggering conditions of the first action are satisfied. If so, it moves to the second state, inject the fault of the first action, and watches for the conditions of the second action.

## Impact
This feature will enable Sieve to test any arbitrary perturbation pattern desired by the user rather than the currently supported three patterns. It is an important step for Sieve to be generic and flexible as a testing tool.

## Goals
- Removal of the perturbation `mode` concept
- A new implementation of the test coordinator running as a state machine
- A clean interface for user to programmatically generate test plans


## Milestones
Start date: Feb 18, 2022

Milestone 1 - Implement the new test coordinator and new instrumentation: Feb 24, 2022

Milestone 2 - Convert the old test plans to the new format: Feb 26, 2022

Milestone 3 - Make Sieve able to generate test plans in the new format: Feb 29, 2022

Milestone 4 - Design and implement the interface for users to programmatically generate test plans: Mar 2, 2022

## Proposed Solution

### Proposed way to run Sieve testing
```
python3 sieve.py -c your-controller -s test -p test_plan.yaml
```

### Proposed test plan format
The proposed test plan for testing intermediate-state will be like:
```yaml
testName: xxx
actions:
  - actionType: restartController
    actionTarget: xxx
    trigger:
      definitions:
        - triggerName: cond1
          condition:
            triggerType: onObjectUpdate
            resourceKey: xxx
            prevState: xxx
            curState: xxx
            repeat: 1
          observationPoint:
            timing: afterControllerWrite
            observeBy: xxx
      expression: cond1
```
- `testName`: the test case to run
- `actions`: a list of actions that the coordinator should take
- `actionType`: we should support at least `restartController`, `killController`, `startController`, `pauseController`, `resumeController`, `pauseAPIServer`, `resumeAPIServer`
- `actionTarget`: which controller to restart
- `trigger`: the triggers that should be satisfied before taking the action organized
- `definitions`: definitions of the triggers
- `triggerType`: we should support at least `onObjectUpdate`, `onAnyFieldModified`, `onAllFieldsModified`, `onObjectCreation`, `onObjectDeletion`, `onTimeout`, `none`
- `conditionName`: mainly used in `expression`
- `resourceKey`: it should be `resource_type/namespace/name` (e.g., `pod/default/mypod`) and used to identify a resource
- `prevState`: only applicable for `onObjectUpdate` and used to indicate the particular update to an object
- `curState`: only applicable for `onObjectUpdate` and used to indicate the particular update to an object
- `repeat`: how many times this condition needs to be satisfied
- `observePoint`: only applicable for `onObjectUpdate`, `onAnyFieldModified`, `onAllFieldsModified`, `onObjectCreation`, `onObjectDeletion` and used to decide where the change is observed
- `observeBy`: who makes the observation; it can be some API server or some controller
- `expression`: express the boolean relationship between all the defined triggers as discussed [here](#Proposed-condition-triggers-topology-implementation)

The test plans for other patterns will look similar.


### Proposed test coordinator architecture
The proposed new implementation of Sieve test coordinator consists of two parts: the event monitor and the state machine. During the initialization phase, the test coordinator will read the test plan and initializes the state machine with the test plan.

The event monitor is essentially an RPC server: the instrumented API server and the controller will make an RPC call to the RPC server at each instrumented program point (e.g., when receiving an event from etcd) to notify the coordinator about the new event (i.e., object creation, update, deletion). Upon receiving a notification, the monitor will update an in-memory table with the most recent state shown in the notification. For example, for any notification sent from the program point where the API server receives an event from etcd, the monitor will do the following:
```go
objectState = objectStates[apiserverNameFromRPC]["afterAPIServerRecv"][resourceKeyFromRPC]
objectState.prevState = objectState.curState
objectState.curState = newStateFromRPC
stateNotificationCh <- StateNotification{
    observeBy:      apiserverNameFromRPC,
    observePoint:   "afterAPIServerRecv",
    resourceKey:    resourceKeyFromRPC,
    delta:          objectState,
}
<-blockingChs["afterAPIServerRecv"][apiserverNameFromRPC][resourceKeyFromRPC]
```

The state machine runs in a different goroutine. The state machine maintains the current state and watches for all the events notified by the event monitor. If the triggers get satisfied by the new events, the state machine will progress to the next state.
```go
select {
case stateNotification := <- stateNotificationCh:
    sm.processStateTriggerConditions(stateNotification)
    blockingChs[stateNotification.observeBy][stateNotification.observePoint][stateNotification.resourceKey] <- "release"
case timeoutNotification := <- timeoutNotificationCh:
    sm.processTimeoutTriggerConditions(timeoutNotification)
}
```

Inside the `processStateTriggerConditions`, the state machine will check whether the notification satisfies (one of) the triggers that block the progress to the next state. If so, it marks that trigger as satisfied. If all the triggers are satisfied, it will progress to the next state. If the next trigger is `onTimeout`, it will start a goroutine that sends a timeoutNotification to the timeoutNotificationCh after the specified timeout happens.

### Proposed condition triggers topology implementation
We will also allow the user to specify the topology of the triggers. That is, to progress to the next state, the triggers do not have to be satisfied one by one sequentially. Here is one example of the proposed format to specify the triggers topology in the test plan (some fields are omitted for simplicity): 
```yaml
    trigger:
      definitions:
        - triggerName: cond1
        - triggerName: cond2
        - triggerName: cond3
        - triggerName: cond4
        - triggerName: cond5
        - triggerName: cond6
      expression: cond1;cond2;(cond3|cond4&(cond5;cond6))  
```
The user first defines each trigger with a unique name (fields other than `triggerName` are omitted for simplicity here). The `expression` consists of `triggerName`s and three operators `;`, `&` and `|`:
- `;`: the triggers connected by `;` should be satisfied sequentially
- `&`: both the triggers connected by `&` should be satisfied without any order requirement
- `|`: at least one of the triggers connected by `|` should be satisfied without any order requirement

Regarding the priority, `&` > `|` > `;`.

The test coordinator will construct a graph for each `trigger` of each `action`.
For the above `trigger`, the graph is constructed as follows:
```
cond1 -> cond2 -> cond3 -> *
             |--> cond4 ---------> *
             |--> cond5 -> cond6 --^
```
Each trigger can be satisfied only when all the preceding triggers are satisfied. When reaching to `*`, the state machine can move to the next state.

## Testability

We can use the CI workflow to test whether all the previously-found bugs can still be detected after implementing this feature
