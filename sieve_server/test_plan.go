package main

import (
	"log"
)

type Action struct {
	actionType   string
	actionTarget string
	triggerGraph *TriggerGraph
}

type TestPlan struct {
	actions []Action
}

func parseTestPlan(raw map[interface{}]interface{}) *TestPlan {
	rawActions, ok := raw["actions"]
	if !ok {
		log.Fatal("actions not found in test plan")
	}
	actions := rawActions.([]interface{})
	for _, rawAction := range actions {
		action := rawAction.(map[interface{}]interface{})
		rawTrigger, ok := action["trigger"]
		if !ok {
			log.Fatal("trigger not found in action")
		}
		trigger := rawTrigger.(map[interface{}]interface{})
		expressionRaw, ok := trigger["expression"]
		if !ok {
			log.Fatal("expression not found in action")
		}
		expression := expressionRaw.(string)
		infix := expressionToInfixTokens(expression)
		printExpression(infix)
		prefix := infixToPrefix(infix)
		printExpression(prefix)
		binaryTreeRoot := prefixExpressionToBinaryTree(prefix)
		triggerGraph := binaryTreeToTriggerGraph(binaryTreeRoot)
		printTriggerGraph(triggerGraph)
	}
	return nil
}

func printExpression(exp []string) {
	log.Printf("%v", exp)
}

func printTriggerNode(triggerNode *TriggerNode) {
	log.Printf("node name: %s, node type: %s\n", triggerNode.nodeName, triggerNode.nodeType)
	for _, successor := range triggerNode.successors {
		log.Printf("successor: %s\n", successor.nodeName)
	}
}

func printTriggerGraph(triggerGraph *TriggerGraph) {
	for _, source := range triggerGraph.sources {
		printTriggerNode(source)
	}
}
