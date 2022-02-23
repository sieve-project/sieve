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
	nodeType   string
	nodeName   string
	successors []*TriggerNode
}

func (tn *TriggerNode) addSuccessors(nodes []*TriggerNode) {
	tn.successors = append(tn.successors, nodes...)
}

type TriggerGraph struct {
	sources []*TriggerNode
	sink    *TriggerNode
}

func prefixExpressionToBinaryTree(prefix []string) *TreeNode {
	tokenStack := NewStack()
	treeNodesMap := map[string]*TreeNode{}
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

func binaryTreeToTriggerNode(node *TreeNode) ([]*TriggerNode, *TriggerNode) {
	switch node.name {
	case ";":
		sourcesOfLeft, sinkOfLeft := binaryTreeToTriggerNode(node.left)
		sourcesOfRight, sinkOfRight := binaryTreeToTriggerNode(node.right)
		sinkOfLeft.addSuccessors(sourcesOfRight)
		return sourcesOfLeft, sinkOfRight
	case "&":
		sourcesOfLeft, sinkOfLeft := binaryTreeToTriggerNode(node.left)
		sourcesOfRight, sinkOfRight := binaryTreeToTriggerNode(node.right)
		triggerAndNode := &TriggerNode{
			nodeType:   And,
			nodeName:   node.composedName,
			successors: []*TriggerNode{},
		}
		sinkOfLeft.addSuccessors([]*TriggerNode{triggerAndNode})
		sinkOfRight.addSuccessors([]*TriggerNode{triggerAndNode})
		sources := append(sourcesOfLeft, sourcesOfRight...)
		return sources, triggerAndNode
	case "|":
		sourcesOfLeft, sinkOfLeft := binaryTreeToTriggerNode(node.left)
		sourcesOfRight, sinkOfRight := binaryTreeToTriggerNode(node.right)
		triggerOrNode := &TriggerNode{
			nodeType:   Or,
			nodeName:   node.composedName,
			successors: []*TriggerNode{},
		}
		sinkOfLeft.addSuccessors([]*TriggerNode{triggerOrNode})
		sinkOfRight.addSuccessors([]*TriggerNode{triggerOrNode})
		sources := append(sourcesOfLeft, sourcesOfRight...)
		return sources, triggerOrNode
	default:
		triggerLiteralNode := &TriggerNode{
			nodeType:   Literal,
			nodeName:   node.name,
			successors: []*TriggerNode{},
		}
		return []*TriggerNode{triggerLiteralNode}, triggerLiteralNode
	}
}

func binaryTreeToTriggerGraph(node *TreeNode) *TriggerGraph {
	sources, sink := binaryTreeToTriggerNode(node)
	triggerGraph := &TriggerGraph{
		sources: sources,
		sink:    sink,
	}
	return triggerGraph
}
