package main

import (
	"log"
	"time"
)

type StateMachine struct {
	states                       []Action
	nextState                    int
	stateNotificationCh          chan TriggerNotification
	timeoutNotificationCh        chan TriggerNotification
	apiServerPauseNotificationCh chan *APIServerPauseNotification
	actionConext                 *ActionContext
}

func NewStateMachine(testPlan *TestPlan, stateNotificationCh chan TriggerNotification, apiServerPauseNotificationCh chan *APIServerPauseNotification, actionContext *ActionContext) *StateMachine {
	return &StateMachine{
		states:                       testPlan.actions,
		nextState:                    0,
		stateNotificationCh:          stateNotificationCh,
		timeoutNotificationCh:        make(chan TriggerNotification, 500),
		apiServerPauseNotificationCh: apiServerPauseNotificationCh,
		actionConext:                 actionContext,
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
	sentBack := false
	if sm.nextState >= len(sm.states) {
		return
	}

	defer func() {
		if !sentBack {
			if blockingCh := notification.getBlockingCh(); blockingCh != nil {
				log.Println("release the blocking ch")
				blockingCh <- "release"
			}
		}
	}()

	action := sm.states[sm.nextState]
	triggerGraph := sm.states[sm.nextState].getTriggerGraph()
	triggerDefinitions := sm.states[sm.nextState].getTriggerDefinitions()
	for triggerName := range triggerGraph.toSatisfy {
		triggerDefinition := triggerDefinitions[triggerName]
		if triggerDefinition.satisfy(notification) {
			triggerGraph.trigger(triggerName)
			log.Printf("trigger %s is satisfied\n", triggerName)
			if triggerGraph.fullyTriggered() {
				log.Printf("all triggers are satisfied for action %d\n", sm.nextState)
				if action.isAsync() {
					if blockingCh := notification.getBlockingCh(); blockingCh != nil {
						log.Println("release the blocking ch earlier due to async")
						blockingCh <- "release"
						sentBack = true
					}
				}
				action.run(sm.actionConext)
				sm.nextState += 1
				if sm.nextState >= len(sm.states) {
					log.Println("all actions are done")
				} else {
					sm.setTimeoutForTimeoutTriggers()
				}
				break
			} else {
				sm.setTimeoutForTimeoutTriggers()
			}
		}
	}
}

func (sm *StateMachine) processAPIServerPause(notification *APIServerPauseNotification) {
	go func() {
		if notification.pausedByAll {
			log.Printf("Start to pause API server for %s\n", notification.apiServerName)
			pausingCh := sm.actionConext.apiserverLocks[notification.apiServerName]["all"]
			<-pausingCh
		} else {
			log.Printf("Start to pause API server for %s %s\n", notification.apiServerName, notification.resourceKey)
			pausingCh := sm.actionConext.apiserverLocks[notification.apiServerName][notification.resourceKey]
			<-pausingCh
		}
		log.Printf("Pause API server done")
		blockingCh := notification.getBlockingCh()
		blockingCh <- "release"
	}()
}

func (sm *StateMachine) run() {
	for {
		select {
		case stateNotification := <-sm.stateNotificationCh:
			sm.processNotification(stateNotification)
		case timeoutNotification := <-sm.timeoutNotificationCh:
			sm.processNotification(timeoutNotification)
		case apiServerNotification := <-sm.apiServerPauseNotificationCh:
			sm.processAPIServerPause(apiServerNotification)
		}
	}
}
