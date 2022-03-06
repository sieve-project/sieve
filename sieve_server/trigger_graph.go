package main

import (
	"fmt"
	"log"
)

type TreeNode struct {
	name         string
	composedName string
	left         *TreeNode
	right        *TreeNode
}

const (
	Literal string = "Literal"
	And     string = "And"
	Or      string = "Or"
)

type TriggerNode struct {
	nodeType     string
	nodeName     string
	predecessors []*TriggerNode
	successors   []*TriggerNode
}

func (tn *TriggerNode) addPredecessors(nodes []*TriggerNode) {
	tn.predecessors = append(tn.predecessors, nodes...)
}

func (tn *TriggerNode) addSuccessors(nodes []*TriggerNode) {
	tn.successors = append(tn.successors, nodes...)
}

type TriggerGraph struct {
	sources   []*TriggerNode
	sink      *TriggerNode
	allNodes  map[string]*TriggerNode
	toSatisfy map[string]struct{}
	satisfied map[string]struct{}
}

func (tg *TriggerGraph) fullyTriggered() bool {
	_, ok := tg.satisfied[tg.sink.nodeName]
	return ok
}

func (tg *TriggerGraph) trigger(nodeName string) {
	_, ok := tg.toSatisfy[nodeName]
	if !ok {
		log.Fatalf("%s not in toSatisfy", nodeName)
	}
	_, ok = tg.satisfied[nodeName]
	if ok {
		log.Fatalf("%s in satisfied", nodeName)
	}
	if tg.allNodes[nodeName].nodeType != Literal {
		log.Fatalf("%s is not literal", nodeName)
	}
	tg.satisfied[nodeName] = exists
	delete(tg.toSatisfy, nodeName)
	for _, successor := range tg.allNodes[nodeName].successors {
		tg.toSatisfy[successor.nodeName] = exists
		if successor.nodeType == Or {
			tg.triggerOrAnd(successor.nodeName)
		} else if successor.nodeType == And {
			andIsTriggered := true
			for _, predecessor := range successor.predecessors {
				if _, ok := tg.satisfied[predecessor.nodeName]; !ok {
					andIsTriggered = false
				}
			}
			if andIsTriggered {
				tg.triggerOrAnd(successor.nodeName)
			}
		}
	}
}

func (tg *TriggerGraph) triggerOrAnd(nodeName string) {
	_, ok := tg.toSatisfy[nodeName]
	if !ok {
		log.Fatalf("%s not in toSatisfy", nodeName)
	}
	_, ok = tg.satisfied[nodeName]
	if ok {
		log.Fatalf("%s in satisfied", nodeName)
	}
	if tg.allNodes[nodeName].nodeType != Or && tg.allNodes[nodeName].nodeType != And {
		log.Fatalf("%s is not Or nor And", nodeName)
	}
	tg.satisfied[nodeName] = exists
	delete(tg.toSatisfy, nodeName)
	for _, successor := range tg.allNodes[nodeName].successors {
		tg.toSatisfy[successor.nodeName] = exists
		if successor.nodeType == Or {
			tg.triggerOrAnd(successor.nodeName)
		} else if successor.nodeType == And {
			andIsTriggered := true
			for _, predecessor := range successor.predecessors {
				if _, ok := tg.satisfied[predecessor.nodeName]; !ok {
					andIsTriggered = false
				}
			}
			if andIsTriggered {
				tg.triggerOrAnd(successor.nodeName)
			}
		}
	}
}

func prefixExpressionToBinaryTree(prefix []string) *TreeNode {
	tokenStack := NewStack()
	treeNodesMap := map[string]*TreeNode{}
	log.Println(prefix)
	for i := len(prefix) - 1; i >= 0; i-- {
		token := prefix[i]
		if !isOperator(prefix[i]) {
			operand := token
			tokenStack.Push(operand)
			treeNode := &TreeNode{
				name:         operand,
				composedName: operand,
				left:         nil,
				right:        nil,
			}
			if _, ok := treeNodesMap[operand]; ok {
				log.Fatalf("%s already found in treeNodesMap", operand)
			}
			treeNodesMap[operand] = treeNode
		} else {
			operator := token
			operand1 := tokenStack.Pop()
			operand2 := tokenStack.Pop()
			composedToken := fmt.Sprintf("(%s%s%s)", operand1, operator, operand2)
			tokenStack.Push(composedToken)
			treeNode := &TreeNode{
				name:         operator,
				composedName: composedToken,
				left:         treeNodesMap[operand1],
				right:        treeNodesMap[operand2],
			}
			if _, ok := treeNodesMap[composedToken]; ok {
				log.Fatalf("%s already found in treeNodesMap", composedToken)
			}
			treeNodesMap[composedToken] = treeNode
		}
	}
	return treeNodesMap[tokenStack.Pop()]
}

func binaryTreeToTriggerNode(node *TreeNode, allNodes map[string]*TriggerNode) ([]*TriggerNode, *TriggerNode) {
	switch node.name {
	case ";":
		sourcesOfLeft, sinkOfLeft := binaryTreeToTriggerNode(node.left, allNodes)
		sourcesOfRight, sinkOfRight := binaryTreeToTriggerNode(node.right, allNodes)
		sinkOfLeft.addSuccessors(sourcesOfRight)
		for idx := range sourcesOfRight {
			sourcesOfRight[idx].addPredecessors([]*TriggerNode{sinkOfLeft})
		}
		return sourcesOfLeft, sinkOfRight
	case "&":
		sourcesOfLeft, sinkOfLeft := binaryTreeToTriggerNode(node.left, allNodes)
		sourcesOfRight, sinkOfRight := binaryTreeToTriggerNode(node.right, allNodes)
		triggerAndNode := &TriggerNode{
			nodeType:     And,
			nodeName:     node.composedName,
			predecessors: []*TriggerNode{sinkOfLeft, sinkOfRight},
			successors:   []*TriggerNode{},
		}
		sinkOfLeft.addSuccessors([]*TriggerNode{triggerAndNode})
		sinkOfRight.addSuccessors([]*TriggerNode{triggerAndNode})
		sources := append(sourcesOfLeft, sourcesOfRight...)
		allNodes[node.composedName] = triggerAndNode
		return sources, triggerAndNode
	case "|":
		sourcesOfLeft, sinkOfLeft := binaryTreeToTriggerNode(node.left, allNodes)
		sourcesOfRight, sinkOfRight := binaryTreeToTriggerNode(node.right, allNodes)
		triggerOrNode := &TriggerNode{
			nodeType:     Or,
			nodeName:     node.composedName,
			predecessors: []*TriggerNode{sinkOfLeft, sinkOfRight},
			successors:   []*TriggerNode{},
		}
		sinkOfLeft.addSuccessors([]*TriggerNode{triggerOrNode})
		sinkOfRight.addSuccessors([]*TriggerNode{triggerOrNode})
		sources := append(sourcesOfLeft, sourcesOfRight...)
		allNodes[node.composedName] = triggerOrNode
		return sources, triggerOrNode
	default:
		triggerLiteralNode := &TriggerNode{
			nodeType:     Literal,
			nodeName:     node.composedName,
			predecessors: []*TriggerNode{},
			successors:   []*TriggerNode{},
		}
		allNodes[node.composedName] = triggerLiteralNode
		return []*TriggerNode{triggerLiteralNode}, triggerLiteralNode
	}
}

func binaryTreeToTriggerGraph(node *TreeNode) *TriggerGraph {
	allNodes := map[string]*TriggerNode{}
	sources, sink := binaryTreeToTriggerNode(node, allNodes)
	toSatisfy := map[string]struct{}{}
	for _, source := range sources {
		toSatisfy[source.nodeName] = exists
	}
	triggerGraph := &TriggerGraph{
		sources:   sources,
		sink:      sink,
		allNodes:  allNodes,
		toSatisfy: toSatisfy,
		satisfied: map[string]struct{}{},
	}
	return triggerGraph
}
