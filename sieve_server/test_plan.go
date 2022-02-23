package main

import (
	"log"
)

const (
	onObjectCreate string = "onObjectCreate"
	onObjectDelete string = "onObjectDelete"
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

func (tt *TimeoutTrigger) getTriggerName() string {
	return tt.name
}

func (tt *TimeoutTrigger) satisfy(triggerNotification TriggerNotification) bool {
	if notification, ok := triggerNotification.(*TimeoutNotification); ok {
		if notification.conditionName == tt.name {
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

func (oct *ObjectCreateTrigger) getTriggerName() string {
	return oct.name
}

func (oct *ObjectCreateTrigger) satisfy(triggerNotification TriggerNotification) bool {
	if notification, ok := triggerNotification.(*ObjectCreateNotification); ok {
		if notification.resourceKey == oct.resourceKey && notification.observedWhen == oct.observedWhen && notification.observedBy == oct.observedBy {
			oct.currentRepeat += 1
			if oct.currentRepeat == oct.desiredRepeat {
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

func (odt *ObjectDeleteTrigger) getTriggerName() string {
	return odt.name
}

func (odt *ObjectDeleteTrigger) satisfy(triggerNotification TriggerNotification) bool {
	if notification, ok := triggerNotification.(*ObjectDeleteNotification); ok {
		if notification.resourceKey == odt.resourceKey && notification.observedWhen == odt.observedWhen && notification.observedBy == odt.observedBy {
			odt.currentRepeat += 1
			if odt.currentRepeat == odt.desiredRepeat {
				return true
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

type RestartControllerAction struct {
	controllerLabel    string
	triggerGraph       *TriggerGraph
	triggerDefinitions map[string]TriggerDefinition
}

func (rca *RestartControllerAction) getTriggerGraph() *TriggerGraph {
	return rca.triggerGraph
}

func (rca *RestartControllerAction) getTriggerDefinitions() map[string]TriggerDefinition {
	return rca.triggerDefinitions
}

func (rca *RestartControllerAction) run(actionConext *ActionContext) {
	log.Println("run the RestartControllerAction")
	restartControllerHelper(actionConext.namespace, rca.controllerLabel, actionConext.leadingAPIServer)
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
	switch actionType {
	case restartController:
		return &RestartControllerAction{
			controllerLabel:    raw["controllerLabel"].(string),
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
