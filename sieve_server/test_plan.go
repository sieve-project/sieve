package main

import (
	"log"
)

const (
	onObjectCreate string = "onObjectCreate"
	onObjectDelete string = "onObjectDelete"
	onObjectUpdate string = "onObjectUpdate"
	onTimeout      string = "onTimeout"
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
	name          string
	resourceKey   string
	prevStateDiff map[string]interface{}
	curStateDiff  map[string]interface{}
	desiredRepeat int
	currentRepeat int
	observedWhen  string
	observedBy    string
}

func (t *ObjectUpdateTrigger) getTriggerName() string {
	return t.name
}

func (t *ObjectUpdateTrigger) satisfy(triggerNotification TriggerNotification) bool {
	if notification, ok := triggerNotification.(*ObjectUpdateNotification); ok {
		if notification.resourceKey == t.resourceKey && notification.observedWhen == t.observedWhen && notification.observedBy == t.observedBy {
			// compute state diff
			exactMatch := true
			if notification.observedWhen == beforeAPIServerRecv || notification.observedWhen == afterAPIServerRecv {
				exactMatch = false
			}
			log.Println(notification.fieldKeyMask)
			log.Println(notification.fieldPathMask)
			if isDesiredUpdate(notification.prevState, notification.curState, t.prevStateDiff, t.curStateDiff, notification.fieldKeyMask, notification.fieldPathMask, exactMatch) {
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
	run(*ActionContext)
}

type PauseAPIServerAction struct {
	apiServerName      string
	async              bool
	triggerGraph       *TriggerGraph
	triggerDefinitions map[string]TriggerDefinition
}

func (a *PauseAPIServerAction) getTriggerGraph() *TriggerGraph {
	return a.triggerGraph
}

func (a *PauseAPIServerAction) getTriggerDefinitions() map[string]TriggerDefinition {
	return a.triggerDefinitions
}

func (a *PauseAPIServerAction) run(actionConext *ActionContext) {
	log.Println("run the PauseAPIServerAction")
	// if a.async {
	// 	// do something
	// } else {
	// 	// do something
	// }
}

type ResumeAPIServerAction struct {
	apiServerName      string
	async              bool
	triggerGraph       *TriggerGraph
	triggerDefinitions map[string]TriggerDefinition
}

func (a *ResumeAPIServerAction) getTriggerGraph() *TriggerGraph {
	return a.triggerGraph
}

func (a *ResumeAPIServerAction) getTriggerDefinitions() map[string]TriggerDefinition {
	return a.triggerDefinitions
}

func (a *ResumeAPIServerAction) run(actionConext *ActionContext) {
	log.Println("run the ResumeAPIServerAction")
	// if a.async {
	// 	// do something
	// } else {
	// 	// do something
	// }
}

type RestartControllerAction struct {
	controllerLabel    string
	async              bool
	triggerGraph       *TriggerGraph
	triggerDefinitions map[string]TriggerDefinition
}

func (a *RestartControllerAction) getTriggerGraph() *TriggerGraph {
	return a.triggerGraph
}

func (a *RestartControllerAction) getTriggerDefinitions() map[string]TriggerDefinition {
	return a.triggerDefinitions
}

func (a *RestartControllerAction) run(actionConext *ActionContext) {
	log.Println("run the RestartControllerAction")
	if a.async {
		go restartAndreconnectController(actionConext.namespace, a.controllerLabel, actionConext.leadingAPIServer, "", false)
	} else {
		restartAndreconnectController(actionConext.namespace, a.controllerLabel, actionConext.leadingAPIServer, "", false)
	}
}

type ReconnectControllerAction struct {
	controllerLabel    string
	reconnectAPIServer string
	async              bool
	triggerGraph       *TriggerGraph
	triggerDefinitions map[string]TriggerDefinition
}

func (a *ReconnectControllerAction) getTriggerGraph() *TriggerGraph {
	return a.triggerGraph
}

func (a *ReconnectControllerAction) getTriggerDefinitions() map[string]TriggerDefinition {
	return a.triggerDefinitions
}

func (a *ReconnectControllerAction) run(actionConext *ActionContext) {
	log.Println("run the ReconnectControllerAction")
	// if a.async {
	// 	go restartAndreconnectController(actionConext.namespace, a.controllerLabel, actionConext.leadingAPIServer, a.reconnectAPIServer, true)
	// } else {
	// 	restartAndreconnectController(actionConext.namespace, a.controllerLabel, actionConext.leadingAPIServer, a.reconnectAPIServer, true)
	// }
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
		observationPoint := raw["observationPoint"].(map[interface{}]interface{})
		return &ObjectUpdateTrigger{
			name:          raw["triggerName"].(string),
			resourceKey:   condition["resourceKey"].(string),
			prevStateDiff: strToMap(condition["prevStateDiff"].(string)),
			curStateDiff:  strToMap(condition["curStateDiff"].(string)),
			desiredRepeat: condition["repeat"].(int),
			currentRepeat: 0,
			observedWhen:  observationPoint["when"].(string),
			observedBy:    observationPoint["by"].(string),
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
	if _, ok := raw["async"]; ok {
		async = true
	}
	switch actionType {
	case pauseAPIServer:
		return &PauseAPIServerAction{
			apiServerName:      raw["apiServerName"].(string),
			async:              async,
			triggerGraph:       triggerGraph,
			triggerDefinitions: triggerDefinitions,
		}
	case resumeAPIServer:
		return &ResumeAPIServerAction{
			apiServerName:      raw["apiServerName"].(string),
			async:              async,
			triggerGraph:       triggerGraph,
			triggerDefinitions: triggerDefinitions,
		}
	case restartController:
		return &RestartControllerAction{
			controllerLabel:    raw["controllerLabel"].(string),
			async:              async,
			triggerGraph:       triggerGraph,
			triggerDefinitions: triggerDefinitions,
		}
	case reconnectController:
		return &ReconnectControllerAction{
			controllerLabel:    raw["controllerLabel"].(string),
			reconnectAPIServer: raw["reconnectAPIServer"].(string),
			async:              async,
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
