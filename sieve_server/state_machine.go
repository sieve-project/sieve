package main

import "time"

type StateMachine struct {
	states                   []*Action
	satisfiedTriggerCounters []map[string]int
	nextState                int
	stateNotificationCh      chan TriggerNotification
	timeoutNotificationCh    chan TriggerNotification
}

func NewStateMachine(testPlan *TestPlan, stateNotificationCh chan TriggerNotification) *StateMachine {
	satisfiedTriggerCounters := make([]map[string]int, len(testPlan.actions))
	return &StateMachine{
		states:                   testPlan.actions,
		satisfiedTriggerCounters: satisfiedTriggerCounters,
		nextState:                0,
		stateNotificationCh:      stateNotificationCh,
		timeoutNotificationCh:    make(chan TriggerNotification, 500),
	}
}

func (sm *StateMachine) waitForTimeout(timeoutValue int, triggerName string) {
	time.Sleep(time.Duration(timeoutValue) * time.Second)
	sm.timeoutNotificationCh <- &TimeoutNotification{
		conditionName: triggerName,
	}
}

func (sm *StateMachine) processNotification(notification TriggerNotification) {
	triggerGraph := sm.states[sm.nextState].triggerGraph
	triggerDefinitions := sm.states[sm.nextState].triggerDefinitions
	for triggerName := range triggerGraph.toSatisfy {
		triggerDefinition := triggerDefinitions[triggerName]
		if _, ok := sm.satisfiedTriggerCounters[sm.nextState][triggerName]; !ok {
			sm.satisfiedTriggerCounters[sm.nextState][triggerName] = 0
		}
		if triggerDefinition.satisfy(notification, sm.satisfiedTriggerCounters[sm.nextState][triggerName]) {
			triggerGraph.trigger(triggerName)
			if triggerGraph.fullyTriggered() {
				// run the action here
				sm.nextState += 1
				break
			} else {
				for triggerName := range triggerGraph.toSatisfy {
					if timeoutTrigger, ok := triggerDefinitions[triggerName].(*TimeoutTrigger); ok {
						go sm.waitForTimeout(timeoutTrigger.timeoutValue, timeoutTrigger.getTriggerName())
					}
				}
			}
		}
	}
}

func (sm *StateMachine) run() {
	for {
		select {
		case stateNotification := <-sm.stateNotificationCh:
			sm.processNotification(stateNotification)
			blockingCh := stateNotification.getBlockingCh()
			blockingCh <- "release"
		case timeoutNotification := <-sm.timeoutNotificationCh:
			sm.processNotification(timeoutNotification)
		}
	}
}
