package main

import (
	"log"
	"time"
)

const (
	onObjectCreate         string = "onObjectCreate"
	onObjectDelete         string = "onObjectDelete"
	onObjectUpdate         string = "onObjectUpdate"
	onAnyFieldModification string = "onAnyFieldModification"
	onTimeout              string = "onTimeout"
)

type TriggerDefinition interface {
	getTriggerName() string
	satisfy(TriggerNotification) bool
}

type TimeoutTrigger struct {
	name         string
	timeoutValue int
}

func (t *TimeoutTrigger) getTriggerName() string {
	return t.name
}

func (t *TimeoutTrigger) satisfy(triggerNotification TriggerNotification) bool {
	if notification, ok := triggerNotification.(*TimeoutNotification); ok {
		if notification.conditionName == t.name {
			return true
		}
	}
	return false
}

type ObjectCreateTrigger struct {
	name          string
	resourceKey   string
	desiredRepeat int
	currentRepeat int
	observedWhen  string
	observedBy    string
}

func (t *ObjectCreateTrigger) getTriggerName() string {
	return t.name
}

func (t *ObjectCreateTrigger) satisfy(triggerNotification TriggerNotification) bool {
	if notification, ok := triggerNotification.(*ObjectCreateNotification); ok {
		if notification.resourceKey == t.resourceKey && notification.observedWhen == t.observedWhen && notification.observedBy == t.observedBy {
			t.currentRepeat += 1
			if t.currentRepeat == t.desiredRepeat {
				return true
			}
		}
	}
	return false
}

type ObjectDeleteTrigger struct {
	name          string
	resourceKey   string
	desiredRepeat int
	currentRepeat int
	observedWhen  string
	observedBy    string
}

func (t *ObjectDeleteTrigger) getTriggerName() string {
	return t.name
}

func (t *ObjectDeleteTrigger) satisfy(triggerNotification TriggerNotification) bool {
	if notification, ok := triggerNotification.(*ObjectDeleteNotification); ok {
		if notification.resourceKey == t.resourceKey && notification.observedWhen == t.observedWhen && notification.observedBy == t.observedBy {
			t.currentRepeat += 1
			if t.currentRepeat == t.desiredRepeat {
				return true
			}
		}
	}
	return false
}

type ObjectUpdateTrigger struct {
	name                  string
	resourceKey           string
	prevStateDiff         map[string]interface{}
	curStateDiff          map[string]interface{}
	convertStateToAPIForm bool
	desiredRepeat         int
	currentRepeat         int
	observedWhen          string
	observedBy            string
}

func (t *ObjectUpdateTrigger) getTriggerName() string {
	return t.name
}

func (t *ObjectUpdateTrigger) satisfy(triggerNotification TriggerNotification) bool {
	if notification, ok := triggerNotification.(*ObjectUpdateNotification); ok {
		if notification.resourceKey == t.resourceKey && notification.observedWhen == t.observedWhen && notification.observedBy == t.observedBy {
			if t.prevStateDiff == nil && t.curStateDiff == nil {
				return true
			}
			// compute state diff
			exactMatch := true
			if notification.observedWhen == beforeAPIServerRecv || notification.observedWhen == afterAPIServerRecv {
				exactMatch = false
			}
			var fieldKeyMaskToUse map[string]struct{}
			var fieldPathMaskToUse map[string]struct{}
			if t.convertStateToAPIForm {
				fieldKeyMaskToUse = notification.fieldKeyMaskAPIForm
				fieldPathMaskToUse = notification.fieldPathMaskAPIForm
			} else {
				fieldKeyMaskToUse = notification.fieldKeyMask
				fieldPathMaskToUse = notification.fieldPathMask
			}
			log.Println(fieldKeyMaskToUse)
			log.Println(fieldPathMaskToUse)
			if isDesiredUpdate(notification.prevState, notification.curState, t.prevStateDiff, t.curStateDiff, fieldKeyMaskToUse, fieldPathMaskToUse, exactMatch) {
				t.currentRepeat += 1
				if t.currentRepeat == t.desiredRepeat {
					return true
				}
			}
		}
	}
	return false
}

type AnyFieldModificationTrigger struct {
	name                  string
	resourceKey           string
	prevStateDiff         map[string]interface{}
	convertStateToAPIForm bool
	desiredRepeat         int
	currentRepeat         int
	observedWhen          string
	observedBy            string
}

func (t *AnyFieldModificationTrigger) getTriggerName() string {
	return t.name
}

func (t *AnyFieldModificationTrigger) satisfy(triggerNotification TriggerNotification) bool {
	if notification, ok := triggerNotification.(*ObjectUpdateNotification); ok {
		if notification.resourceKey == t.resourceKey && notification.observedWhen == t.observedWhen && notification.observedBy == t.observedBy {
			var fieldKeyMaskToUse map[string]struct{}
			var fieldPathMaskToUse map[string]struct{}
			if t.convertStateToAPIForm {
				fieldKeyMaskToUse = notification.fieldKeyMaskAPIForm
				fieldPathMaskToUse = notification.fieldPathMaskAPIForm
			} else {
				fieldKeyMaskToUse = notification.fieldKeyMask
				fieldPathMaskToUse = notification.fieldPathMask
			}
			log.Println(fieldKeyMaskToUse)
			log.Println(fieldPathMaskToUse)
			if isAnyFieldModified(notification.curState, t.prevStateDiff, fieldKeyMaskToUse, fieldPathMaskToUse) {
				t.currentRepeat += 1
				if t.currentRepeat == t.desiredRepeat {
					return true
				}
			}
		}
	}
	return false
}

type Action interface {
	getTriggerGraph() *TriggerGraph
	getTriggerDefinitions() map[string]TriggerDefinition
	isAsync() bool
	run(*ActionContext)
}

type PauseAPIServerAction struct {
	apiServerName      string
	pauseScope         string
	async              bool
	waitBefore         int
	waitAfter          int
	triggerGraph       *TriggerGraph
	triggerDefinitions map[string]TriggerDefinition
}

func (a *PauseAPIServerAction) getTriggerGraph() *TriggerGraph {
	return a.triggerGraph
}

func (a *PauseAPIServerAction) getTriggerDefinitions() map[string]TriggerDefinition {
	return a.triggerDefinitions
}

func (a *PauseAPIServerAction) isAsync() bool {
	return a.async
}

func (a *PauseAPIServerAction) runInternal(actionContext *ActionContext, async bool) {
	log.Println("run the PauseAPIServerAction")
	if a.waitBefore > 0 {
		time.Sleep(time.Duration(a.waitBefore) * time.Second)
	}
	if _, ok := actionContext.apiserverLockedMap[a.apiServerName]; !ok {
		actionContext.apiserverLockedMap[a.apiServerName] = map[string]bool{}
	}
	if _, ok := actionContext.apiserverLocks[a.apiServerName]; !ok {
		actionContext.apiserverLocks[a.apiServerName] = map[string]chan string{}
	}
	log.Printf("Create channel for %s %s\n", a.apiServerName, a.pauseScope)
	if _, ok := actionContext.apiserverLocks[a.apiServerName][a.pauseScope]; !ok {
		actionContext.apiserverLocks[a.apiServerName][a.pauseScope] = make(chan string)
	}
	actionContext.apiserverLockedMap[a.apiServerName][a.pauseScope] = true
	if a.waitAfter > 0 {
		time.Sleep(time.Duration(a.waitAfter) * time.Second)
	}
	if async {
		actionContext.asyncDoneCh <- &AsyncDoneNotification{}
	}
	log.Println("PauseAPIServerAction done")
}

func (a *PauseAPIServerAction) run(actionContext *ActionContext) {
	if a.async {
		go a.runInternal(actionContext, true)
	} else {
		a.runInternal(actionContext, false)
	}
}

type ResumeAPIServerAction struct {
	apiServerName      string
	pauseScope         string
	async              bool
	waitBefore         int
	waitAfter          int
	triggerGraph       *TriggerGraph
	triggerDefinitions map[string]TriggerDefinition
}

func (a *ResumeAPIServerAction) getTriggerGraph() *TriggerGraph {
	return a.triggerGraph
}

func (a *ResumeAPIServerAction) getTriggerDefinitions() map[string]TriggerDefinition {
	return a.triggerDefinitions
}

func (a *ResumeAPIServerAction) isAsync() bool {
	return a.async
}

func (a *ResumeAPIServerAction) runInternal(actionContext *ActionContext, async bool) {
	log.Println("run the ResumeAPIServerAction")
	if a.waitBefore > 0 {
		time.Sleep(time.Duration(a.waitBefore) * time.Second)
	}
	log.Printf("Close channel for %s %s\n", a.apiServerName, a.pauseScope)
	actionContext.apiserverLocks[a.apiServerName][a.pauseScope] <- "release"
	close(actionContext.apiserverLocks[a.apiServerName][a.pauseScope])
	actionContext.apiserverLockedMap[a.apiServerName][a.pauseScope] = false
	if a.waitAfter > 0 {
		time.Sleep(time.Duration(a.waitAfter) * time.Second)
	}
	if async {
		actionContext.asyncDoneCh <- &AsyncDoneNotification{}
	}
	log.Println("ResumeAPIServerAction done")
}

func (a *ResumeAPIServerAction) run(actionContext *ActionContext) {
	if a.async {
		go a.runInternal(actionContext, true)
	} else {
		a.runInternal(actionContext, false)
	}
}

type PauseControllerReadAction struct {
	pauseScope         string
	pauseAt            string
	avoidOngoingRead   bool
	async              bool
	waitBefore         int
	waitAfter          int
	triggerGraph       *TriggerGraph
	triggerDefinitions map[string]TriggerDefinition
}

func (a *PauseControllerReadAction) getTriggerGraph() *TriggerGraph {
	return a.triggerGraph
}

func (a *PauseControllerReadAction) getTriggerDefinitions() map[string]TriggerDefinition {
	return a.triggerDefinitions
}

func (a *PauseControllerReadAction) isAsync() bool {
	return a.async
}

func (a *PauseControllerReadAction) runInternal(actionContext *ActionContext, async bool) {
	log.Println("run the PauseControllerReadAction")
	if a.waitBefore > 0 {
		time.Sleep(time.Duration(a.waitBefore) * time.Second)
	}

	actionContext.pauseControllerSharedDataLock.Lock()
	if _, ok := actionContext.controllerPausingChs[a.pauseAt]; !ok {
		actionContext.controllerPausingChs[a.pauseAt] = map[string]chan string{}
	}
	log.Printf("Create channel for %s %s\n", a.pauseAt, a.pauseScope)
	if _, ok := actionContext.controllerPausingChs[a.pauseAt][a.pauseScope]; !ok {
		actionContext.controllerPausingChs[a.pauseAt][a.pauseScope] = make(chan string)
	}

	if _, ok := actionContext.controllerShouldPauseMap[a.pauseAt]; !ok {
		actionContext.controllerShouldPauseMap[a.pauseAt] = map[string]bool{}
	}
	actionContext.controllerShouldPauseMap[a.pauseAt][a.pauseScope] = true
	actionContext.pauseControllerSharedDataLock.Unlock()

	if a.waitAfter > 0 {
		time.Sleep(time.Duration(a.waitAfter) * time.Second)
	}
	if async {
		actionContext.asyncDoneCh <- &AsyncDoneNotification{}
	}
	if a.avoidOngoingRead {
		actionContext.controllerOngoingReadLock.Lock()
		log.Println("there is no ongoing read now; PauseControllerReadAction can return safely")
		actionContext.controllerOngoingReadLock.Unlock()
	}
	log.Println("PauseControllerReadAction done")
}

func (a *PauseControllerReadAction) run(actionContext *ActionContext) {
	if a.async {
		go a.runInternal(actionContext, true)
	} else {
		a.runInternal(actionContext, false)
	}
}

type ResumeControllerReadAction struct {
	pauseScope         string
	pauseAt            string
	async              bool
	waitBefore         int
	waitAfter          int
	triggerGraph       *TriggerGraph
	triggerDefinitions map[string]TriggerDefinition
}

func (a *ResumeControllerReadAction) getTriggerGraph() *TriggerGraph {
	return a.triggerGraph
}

func (a *ResumeControllerReadAction) getTriggerDefinitions() map[string]TriggerDefinition {
	return a.triggerDefinitions
}

func (a *ResumeControllerReadAction) isAsync() bool {
	return a.async
}

func (a *ResumeControllerReadAction) runInternal(actionContext *ActionContext, async bool) {
	log.Println("run the ResumeControllerReadAction")
	if a.waitBefore > 0 {
		time.Sleep(time.Duration(a.waitBefore) * time.Second)
	}
	log.Printf("Close channel for %s %s\n", a.pauseAt, a.pauseScope)

	actionContext.pauseControllerSharedDataLock.Lock()
	// actionContext.controllerPausingChs[a.pauseAt][a.pauseScope] <- "release"
	close(actionContext.controllerPausingChs[a.pauseAt][a.pauseScope])
	actionContext.controllerShouldPauseMap[a.pauseAt][a.pauseScope] = false
	actionContext.pauseControllerSharedDataLock.Unlock()

	if a.waitAfter > 0 {
		time.Sleep(time.Duration(a.waitAfter) * time.Second)
	}
	if async {
		actionContext.asyncDoneCh <- &AsyncDoneNotification{}
	}
	log.Println("ResumeControllerReadAction done")
}

func (a *ResumeControllerReadAction) run(actionContext *ActionContext) {
	if a.async {
		go a.runInternal(actionContext, true)
	} else {
		a.runInternal(actionContext, false)
	}
}

type PauseControllerWriteAction struct {
	writeTarget        string
	pauseAt            string
	async              bool
	waitBefore         int
	waitAfter          int
	triggerGraph       *TriggerGraph
	triggerDefinitions map[string]TriggerDefinition
}

func (a *PauseControllerWriteAction) getTriggerGraph() *TriggerGraph {
	return a.triggerGraph
}

func (a *PauseControllerWriteAction) getTriggerDefinitions() map[string]TriggerDefinition {
	return a.triggerDefinitions
}

func (a *PauseControllerWriteAction) isAsync() bool {
	return a.async
}

func (a *PauseControllerWriteAction) runInternal(actionContext *ActionContext, async bool) {
	log.Println("run the PauseControllerWriteAction")
	if a.waitBefore > 0 {
		time.Sleep(time.Duration(a.waitBefore) * time.Second)
	}
	// TODO: implement runInternal
	// time.Sleep(5 * time.Second)
	if a.waitAfter > 0 {
		time.Sleep(time.Duration(a.waitAfter) * time.Second)
	}
	if async {
		actionContext.asyncDoneCh <- &AsyncDoneNotification{}
	}
	log.Println("PauseControllerWriteAction done")
}

func (a *PauseControllerWriteAction) run(actionContext *ActionContext) {
	if a.async {
		go a.runInternal(actionContext, true)
	} else {
		a.runInternal(actionContext, false)
	}
}

type ResumeControllerWriteAction struct {
	writeTarget        string
	pauseAt            string
	async              bool
	waitBefore         int
	waitAfter          int
	triggerGraph       *TriggerGraph
	triggerDefinitions map[string]TriggerDefinition
}

func (a *ResumeControllerWriteAction) getTriggerGraph() *TriggerGraph {
	return a.triggerGraph
}

func (a *ResumeControllerWriteAction) getTriggerDefinitions() map[string]TriggerDefinition {
	return a.triggerDefinitions
}

func (a *ResumeControllerWriteAction) isAsync() bool {
	return a.async
}

func (a *ResumeControllerWriteAction) runInternal(actionContext *ActionContext, async bool) {
	log.Println("run the ResumeControllerWriteAction")
	if a.waitBefore > 0 {
		time.Sleep(time.Duration(a.waitBefore) * time.Second)
	}
	// TODO: implement runInternal
	if a.waitAfter > 0 {
		time.Sleep(time.Duration(a.waitAfter) * time.Second)
	}
	if async {
		actionContext.asyncDoneCh <- &AsyncDoneNotification{}
	}
	log.Println("ResumeControllerWriteAction done")
}

func (a *ResumeControllerWriteAction) run(actionContext *ActionContext) {
	if a.async {
		go a.runInternal(actionContext, true)
	} else {
		a.runInternal(actionContext, false)
	}
}

type RestartControllerAction struct {
	controllerLabel    string
	async              bool
	waitBefore         int
	waitAfter          int
	triggerGraph       *TriggerGraph
	triggerDefinitions map[string]TriggerDefinition
}

func (a *RestartControllerAction) getTriggerGraph() *TriggerGraph {
	return a.triggerGraph
}

func (a *RestartControllerAction) getTriggerDefinitions() map[string]TriggerDefinition {
	return a.triggerDefinitions
}

func (a *RestartControllerAction) isAsync() bool {
	return a.async
}

func (a *RestartControllerAction) runInternal(actionContext *ActionContext, async bool) {
	log.Println("run the RestartControllerAction")
	if a.waitBefore > 0 {
		time.Sleep(time.Duration(a.waitBefore) * time.Second)
	}
	restartAndreconnectController(actionContext.namespace, a.controllerLabel, actionContext.leadingAPIServer, "", false)
	if a.waitAfter > 0 {
		time.Sleep(time.Duration(a.waitAfter) * time.Second)
	}
	if async {
		actionContext.asyncDoneCh <- &AsyncDoneNotification{}
	}
	log.Println("RestartControllerAction done")
}

func (a *RestartControllerAction) run(actionContext *ActionContext) {
	if a.async {
		go a.runInternal(actionContext, true)
	} else {
		a.runInternal(actionContext, false)
	}
}

type ReconnectControllerAction struct {
	controllerLabel    string
	reconnectAPIServer string
	async              bool
	waitBefore         int
	waitAfter          int
	triggerGraph       *TriggerGraph
	triggerDefinitions map[string]TriggerDefinition
}

func (a *ReconnectControllerAction) getTriggerGraph() *TriggerGraph {
	return a.triggerGraph
}

func (a *ReconnectControllerAction) getTriggerDefinitions() map[string]TriggerDefinition {
	return a.triggerDefinitions
}

func (a *ReconnectControllerAction) isAsync() bool {
	return a.async
}

func (a *ReconnectControllerAction) runInternal(actionContext *ActionContext, async bool) {
	log.Println("run the ReconnectControllerAction")
	if a.waitBefore > 0 {
		time.Sleep(time.Duration(a.waitBefore) * time.Second)
	}
	restartAndreconnectController(actionContext.namespace, a.controllerLabel, actionContext.leadingAPIServer, a.reconnectAPIServer, true)
	if a.waitAfter > 0 {
		time.Sleep(time.Duration(a.waitAfter) * time.Second)
	}
	if async {
		actionContext.asyncDoneCh <- &AsyncDoneNotification{}
	}
	log.Println("ReconnectControllerAction done")
}

func (a *ReconnectControllerAction) run(actionContext *ActionContext) {
	if a.async {
		go a.runInternal(actionContext, true)
	} else {
		a.runInternal(actionContext, false)
	}
}

type TestPlan struct {
	actions []Action
}

func parseTriggerDefinition(raw map[interface{}]interface{}) TriggerDefinition {
	condition := raw["condition"].(map[interface{}]interface{})
	conditionType := condition["conditionType"].(string)
	switch conditionType {
	case onObjectCreate:
		observationPoint := raw["observationPoint"].(map[interface{}]interface{})
		return &ObjectCreateTrigger{
			name:          raw["triggerName"].(string),
			resourceKey:   condition["resourceKey"].(string),
			desiredRepeat: condition["repeat"].(int),
			currentRepeat: 0,
			observedWhen:  observationPoint["when"].(string),
			observedBy:    observationPoint["by"].(string),
		}
	case onObjectDelete:
		observationPoint := raw["observationPoint"].(map[interface{}]interface{})
		return &ObjectDeleteTrigger{
			name:          raw["triggerName"].(string),
			resourceKey:   condition["resourceKey"].(string),
			desiredRepeat: condition["repeat"].(int),
			currentRepeat: 0,
			observedWhen:  observationPoint["when"].(string),
			observedBy:    observationPoint["by"].(string),
		}
	case onObjectUpdate:
		convertStateToAPIForm := false
		if val, ok := condition["convertStateToAPIForm"]; ok {
			convertStateToAPIForm = val.(bool)
		}
		var prevStateDiff map[string]interface{} = nil
		var curStateDiff map[string]interface{} = nil
		_, ok1 := condition["prevStateDiff"]
		_, ok2 := condition["curStateDiff"]
		if ok1 && ok2 {
			if convertStateToAPIForm {
				prevStateDiff = convertObjectStateToAPIForm(strToMap(condition["prevStateDiff"].(string)))
				curStateDiff = convertObjectStateToAPIForm(strToMap(condition["curStateDiff"].(string)))
			} else {
				prevStateDiff = strToMap(condition["prevStateDiff"].(string))
				curStateDiff = strToMap(condition["curStateDiff"].(string))
			}
		}
		observationPoint := raw["observationPoint"].(map[interface{}]interface{})
		return &ObjectUpdateTrigger{
			name:                  raw["triggerName"].(string),
			resourceKey:           condition["resourceKey"].(string),
			prevStateDiff:         prevStateDiff,
			curStateDiff:          curStateDiff,
			convertStateToAPIForm: convertStateToAPIForm,
			desiredRepeat:         condition["repeat"].(int),
			currentRepeat:         0,
			observedWhen:          observationPoint["when"].(string),
			observedBy:            observationPoint["by"].(string),
		}
	case onAnyFieldModification:
		convertStateToAPIForm := false
		if val, ok := condition["convertStateToAPIForm"]; ok {
			convertStateToAPIForm = val.(bool)
		}
		var prevStateDiff map[string]interface{}
		if convertStateToAPIForm {
			prevStateDiff = convertObjectStateToAPIForm(strToMap(condition["prevStateDiff"].(string)))
		} else {
			prevStateDiff = strToMap(condition["prevStateDiff"].(string))
		}
		observationPoint := raw["observationPoint"].(map[interface{}]interface{})
		return &AnyFieldModificationTrigger{
			name:                  raw["triggerName"].(string),
			resourceKey:           condition["resourceKey"].(string),
			prevStateDiff:         prevStateDiff,
			convertStateToAPIForm: convertStateToAPIForm,
			desiredRepeat:         condition["repeat"].(int),
			currentRepeat:         0,
			observedWhen:          observationPoint["when"].(string),
			observedBy:            observationPoint["by"].(string),
		}
	case onTimeout:
		return &TimeoutTrigger{
			name:         raw["triggerName"].(string),
			timeoutValue: condition["timeoutValue"].(int),
		}
	default:
		log.Fatalf("invalid trigger type %v", conditionType)
		return nil
	}
}

func parseAction(raw map[interface{}]interface{}) Action {
	trigger := raw["trigger"].(map[interface{}]interface{})

	expression := trigger["expression"].(string)
	infix := expressionToInfixTokens(expression)
	prefix := infixToPrefix(infix)
	binaryTreeRoot := prefixExpressionToBinaryTree(prefix)
	triggerGraph := binaryTreeToTriggerGraph(binaryTreeRoot)
	printTriggerGraph(triggerGraph)

	definitions := trigger["definitions"].([]interface{})
	triggerDefinitions := map[string]TriggerDefinition{}
	for _, definition := range definitions {
		triggerDefinition := parseTriggerDefinition(definition.(map[interface{}]interface{}))
		triggerDefinitions[triggerDefinition.getTriggerName()] = triggerDefinition
	}

	actionType := raw["actionType"].(string)
	async := false
	if val, ok := raw["async"]; ok {
		async = val.(bool)
	}
	waitBefore := 0
	if val, ok := raw["waitBefore"]; ok {
		waitBefore = val.(int)
	}
	waitAfter := 0
	if val, ok := raw["waitAfter"]; ok {
		waitAfter = val.(int)
	}

	switch actionType {
	case pauseAPIServer:
		return &PauseAPIServerAction{
			apiServerName:      raw["apiServerName"].(string),
			pauseScope:         raw["pauseScope"].(string),
			async:              async,
			waitBefore:         waitBefore,
			waitAfter:          waitAfter,
			triggerGraph:       triggerGraph,
			triggerDefinitions: triggerDefinitions,
		}
	case resumeAPIServer:
		return &ResumeAPIServerAction{
			apiServerName:      raw["apiServerName"].(string),
			pauseScope:         raw["pauseScope"].(string),
			async:              async,
			waitBefore:         waitBefore,
			waitAfter:          waitAfter,
			triggerGraph:       triggerGraph,
			triggerDefinitions: triggerDefinitions,
		}
	case pauseControllerRead:
		pauseScope := "all"
		if val, ok := raw["pauseScope"]; ok {
			pauseScope = val.(string)
		}
		avoidOngoingRead := false
		if val, ok := raw["avoidOngoingRead"]; ok {
			avoidOngoingRead = val.(bool)
		}
		return &PauseControllerReadAction{
			pauseScope:         pauseScope,
			pauseAt:            raw["pauseAt"].(string),
			avoidOngoingRead:   avoidOngoingRead,
			async:              async,
			waitBefore:         waitBefore,
			waitAfter:          waitAfter,
			triggerGraph:       triggerGraph,
			triggerDefinitions: triggerDefinitions,
		}
	case resumeControllerRead:
		pauseScope := "all"
		if val, ok := raw["pauseScope"]; ok {
			pauseScope = val.(string)
		}
		return &ResumeControllerReadAction{
			pauseScope:         pauseScope,
			pauseAt:            raw["pauseAt"].(string),
			async:              async,
			waitBefore:         waitBefore,
			waitAfter:          waitAfter,
			triggerGraph:       triggerGraph,
			triggerDefinitions: triggerDefinitions,
		}
	case pauseControllerWrite:
		writeTarget := "all"
		if val, ok := raw["writeTarget"]; ok {
			writeTarget = val.(string)
		}
		return &PauseControllerWriteAction{
			writeTarget:        writeTarget,
			pauseAt:            raw["pauseAt"].(string),
			async:              async,
			waitBefore:         waitBefore,
			waitAfter:          waitAfter,
			triggerGraph:       triggerGraph,
			triggerDefinitions: triggerDefinitions,
		}
	case resumeControllerWrite:
		writeTarget := "all"
		if val, ok := raw["writeTarget"]; ok {
			writeTarget = val.(string)
		}
		return &ResumeControllerWriteAction{
			writeTarget:        writeTarget,
			pauseAt:            raw["pauseAt"].(string),
			async:              async,
			waitBefore:         waitBefore,
			waitAfter:          waitAfter,
			triggerGraph:       triggerGraph,
			triggerDefinitions: triggerDefinitions,
		}
	case restartController:
		return &RestartControllerAction{
			controllerLabel:    raw["controllerLabel"].(string),
			async:              async,
			waitBefore:         waitBefore,
			waitAfter:          waitAfter,
			triggerGraph:       triggerGraph,
			triggerDefinitions: triggerDefinitions,
		}
	case reconnectController:
		return &ReconnectControllerAction{
			controllerLabel:    raw["controllerLabel"].(string),
			reconnectAPIServer: raw["reconnectAPIServer"].(string),
			async:              async,
			waitBefore:         waitBefore,
			waitAfter:          waitAfter,
			triggerGraph:       triggerGraph,
			triggerDefinitions: triggerDefinitions,
		}
	default:
		log.Fatalf("invalid action type %s\n", actionType)
		return nil
	}
}

func parseTestPlan(raw map[interface{}]interface{}) *TestPlan {
	actionsInTestPlan := raw["actions"].([]interface{})
	actions := []Action{}
	for _, rawAction := range actionsInTestPlan {
		actionInTestPlan := rawAction.(map[interface{}]interface{})
		action := parseAction(actionInTestPlan)
		actions = append(actions, action)
	}
	return &TestPlan{
		actions: actions,
	}
}

func printExpression(exp []string) {
	log.Printf("%v", exp)
}

func printTriggerNode(triggerNode *TriggerNode) {
	log.Printf("node name: %s, node type: %s\n", triggerNode.nodeName, triggerNode.nodeType)
	for _, predecessor := range triggerNode.predecessors {
		log.Printf("predecessor: %s\n", predecessor.nodeName)
	}
	for _, successor := range triggerNode.successors {
		log.Printf("successor: %s\n", successor.nodeName)
	}
}

func printTriggerGraph(triggerGraph *TriggerGraph) {
	log.Println("all nodes:")
	for _, node := range triggerGraph.allNodes {
		log.Printf("node name: %s\n", node.nodeName)
	}
	log.Println("print each node:")
	for _, node := range triggerGraph.allNodes {
		printTriggerNode(node)
	}
}
