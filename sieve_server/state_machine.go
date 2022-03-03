package main

import (
	"log"
	"time"
)

type StateMachine struct {
	states                 []Action
	nextState              int
	stateNotificationCh    chan TriggerNotification
	timeoutNotificationCh  chan TriggerNotification
	asyncDoneCh            chan *AsyncDoneNotification
	asyncActionInExecution bool
	actionConext           *ActionContext
}

func NewStateMachine(testPlan *TestPlan, stateNotificationCh chan TriggerNotification, asyncDoneCh chan *AsyncDoneNotification, actionContext *ActionContext) *StateMachine {
	return &StateMachine{
		states:                 testPlan.actions,
		nextState:              0,
		stateNotificationCh:    stateNotificationCh,
		timeoutNotificationCh:  make(chan TriggerNotification, 500),
		asyncDoneCh:            asyncDoneCh,
		asyncActionInExecution: false,
		actionConext:           actionContext,
	}
}

func (sm *StateMachine) waitForTimeout(timeoutValue int, triggerName string) {
	time.Sleep(time.Duration(timeoutValue) * time.Second)
	sm.timeoutNotificationCh <- &TimeoutNotification{
		conditionName: triggerName,
	}
}

func (sm *StateMachine) setTimeoutForTimeoutTriggers() {
	triggerGraph := sm.states[sm.nextState].getTriggerGraph()
	triggerDefinitions := sm.states[sm.nextState].getTriggerDefinitions()
	for triggerName := range triggerGraph.toSatisfy {
		if timeoutTrigger, ok := triggerDefinitions[triggerName].(*TimeoutTrigger); ok {
			go sm.waitForTimeout(timeoutTrigger.timeoutValue, timeoutTrigger.getTriggerName())
		}
	}
}

func (sm *StateMachine) processNotification(notification TriggerNotification) {
	defer func() {
		if blockingCh := notification.getBlockingCh(); blockingCh != nil {
			log.Println("release the blocking ch")
			blockingCh <- "release"
		}
	}()
	if sm.nextState >= len(sm.states) {
		// all the actions are finished
		return
	}
	if sm.asyncActionInExecution {
		// do not process triggers before the previous async action gets finished
		return
	}

	action := sm.states[sm.nextState]
	triggerGraph := sm.states[sm.nextState].getTriggerGraph()
	triggerDefinitions := sm.states[sm.nextState].getTriggerDefinitions()
	for triggerName := range triggerGraph.toSatisfy {
		triggerDefinition, foundTrigger := triggerDefinitions[triggerName]
		if !foundTrigger {
			log.Printf("trigger %s is not in the definition table; skip it\n", triggerName)
			continue
		}
		if triggerDefinition.satisfy(notification) {
			triggerGraph.trigger(triggerName)
			log.Printf("trigger %s is satisfied\n", triggerName)
			if triggerGraph.fullyTriggered() {
				log.Printf("all triggers are satisfied for action %d\n", sm.nextState)
				action.run(sm.actionConext)
				if !action.isAsync() {
					sm.nextState += 1
					if sm.nextState >= len(sm.states) {
						log.Println("all actions are done")
					} else {
						sm.setTimeoutForTimeoutTriggers()
					}
				} else {
					sm.asyncActionInExecution = true
				}
				break
			} else {
				sm.setTimeoutForTimeoutTriggers()
			}
		}
	}
}

func (sm *StateMachine) processAsyncDone(notification *AsyncDoneNotification) {
	sm.nextState += 1
	sm.asyncActionInExecution = false
	if sm.nextState >= len(sm.states) {
		log.Println("all actions are done")
	} else {
		sm.setTimeoutForTimeoutTriggers()
	}
}

func (sm *StateMachine) run() {
	for {
		select {
		case stateNotification := <-sm.stateNotificationCh:
			sm.processNotification(stateNotification)
		case timeoutNotification := <-sm.timeoutNotificationCh:
			sm.processNotification(timeoutNotification)
		case asyncDoneNotification := <-sm.asyncDoneCh:
			sm.processAsyncDone(asyncDoneNotification)
		}
	}
}
