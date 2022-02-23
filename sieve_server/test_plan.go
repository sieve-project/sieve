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
}

type TimeoutTrigger struct {
	name         string
	timeoutValue int
}

func (tt *TimeoutTrigger) getTriggerName() string {
	return tt.name
}

type ObjectCreateTrigger struct {
	name         string
	resourceKey  string
	observedWhen string
	observedBy   string
	repeat       int
}

func (oct *ObjectCreateTrigger) getTriggerName() string {
	return oct.name
}

type ObjectDeleteTrigger struct {
	name         string
	resourceKey  string
	observedWhen string
	observedBy   string
	repeat       int
}

func (odt *ObjectDeleteTrigger) getTriggerName() string {
	return odt.name
}

type Action struct {
	actionType         string
	actionTarget       string
	triggerGraph       *TriggerGraph
	triggerDefinitions []TriggerDefinition
}

type TestPlan struct {
	actions []*Action
}

func parseTriggerDefinition(raw map[interface{}]interface{}) TriggerDefinition {
	condition := raw["condition"].(map[interface{}]interface{})
	conditionType := condition["conditionType"].(string)
	switch conditionType {
	case onObjectCreate:
		observationPoint := raw["observationPoint"].(map[interface{}]interface{})
		return &ObjectCreateTrigger{
			name:         raw["triggerName"].(string),
			resourceKey:  condition["resourceKey"].(string),
			repeat:       condition["repeat"].(int),
			observedWhen: observationPoint["when"].(string),
			observedBy:   observationPoint["by"].(string),
		}
	case onObjectDelete:
		observationPoint := raw["observationPoint"].(map[interface{}]interface{})
		return &ObjectDeleteTrigger{
			name:         raw["triggerName"].(string),
			resourceKey:  condition["resourceKey"].(string),
			repeat:       condition["repeat"].(int),
			observedWhen: observationPoint["when"].(string),
			observedBy:   observationPoint["by"].(string),
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

func parseTestPlan(raw map[interface{}]interface{}) *TestPlan {
	actionsInTestPlan := raw["actions"].([]interface{})
	actions := []*Action{}
	for _, rawAction := range actionsInTestPlan {
		actionInTestPlan := rawAction.(map[interface{}]interface{})
		triggerInTestPlan := actionInTestPlan["trigger"].(map[interface{}]interface{})

		expression := triggerInTestPlan["expression"].(string)
		infix := expressionToInfixTokens(expression)
		prefix := infixToPrefix(infix)
		binaryTreeRoot := prefixExpressionToBinaryTree(prefix)
		triggerGraph := binaryTreeToTriggerGraph(binaryTreeRoot)
		printTriggerGraph(triggerGraph)

		definitionsInTestPlan := triggerInTestPlan["definitions"].([]interface{})
		triggerDefinitions := []TriggerDefinition{}
		for _, definition := range definitionsInTestPlan {
			triggerDefinition := parseTriggerDefinition(definition.(map[interface{}]interface{}))
			triggerDefinitions = append(triggerDefinitions, triggerDefinition)
		}

		action := &Action{
			actionType:         actionInTestPlan["actionType"].(string),
			actionTarget:       actionInTestPlan["actionTarget"].(string),
			triggerGraph:       triggerGraph,
			triggerDefinitions: triggerDefinitions,
		}
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
