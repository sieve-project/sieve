package main

import (
	"log"
	"time"
)

type StateMachine struct {
	states                []*Action
	nextState             int
	stateNotificationCh   chan TriggerNotification
	timeoutNotificationCh chan TriggerNotification
}

func NewStateMachine(testPlan *TestPlan, stateNotificationCh chan TriggerNotification) *StateMachine {
	return &StateMachine{
		states:                testPlan.actions,
		nextState:             0,
		stateNotificationCh:   stateNotificationCh,
		timeoutNotificationCh: make(chan TriggerNotification, 500),
	}
}

func (sm *StateMachine) waitForTimeout(timeoutValue int, triggerName string) {
	time.Sleep(time.Duration(timeoutValue) * time.Second)
	sm.timeoutNotificationCh <- &TimeoutNotification{
		conditionName: triggerName,
	}
}

func (sm *StateMachine) processNotification(notification TriggerNotification) {
	if sm.nextState >= len(sm.states) {
		return
	}
	triggerGraph := sm.states[sm.nextState].triggerGraph
	triggerDefinitions := sm.states[sm.nextState].triggerDefinitions
	for triggerName := range triggerGraph.toSatisfy {
		triggerDefinition := triggerDefinitions[triggerName]
		if triggerDefinition.satisfy(notification) {
			triggerGraph.trigger(triggerName)
			if triggerGraph.fullyTriggered() {
				log.Println("all triggers are satisfied")
				// TODO: run the action here
				sm.nextState += 1
				if sm.nextState >= len(sm.states) {
					log.Println("all actions are done")
				}
				break
			} else {
				log.Printf("trigger %s is satisfied\n", triggerName)
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
			log.Println("release the blocking ch")
			blockingCh <- "release"
		case timeoutNotification := <-sm.timeoutNotificationCh:
			sm.processNotification(timeoutNotification)
		}
	}
}
