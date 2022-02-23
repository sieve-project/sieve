package main

import "log"

func reverse(tokens []string) {
	for i, j := 0, len(tokens)-1; i < j; i, j = i+1, j-1 {
		tokens[i], tokens[j] = tokens[j], tokens[i]
	}
}

func isOperator(text string) bool {
	return text == ";" || text == "&" || text == "|" || text == "(" || text == ")"
}

func priority(text string) int {
	if text == ";" {
		return 1
	} else if text == "|" {
		return 2
	} else if text == "&" {
		return 3
	} else if text == "(" {
		return 0
	} else if text == ")" {
		return 0
	}
	log.Fatalf("invalid operator %s\n", text)
	return -1
}

func expressionToInfixTokens(exp string) []string {
	tokens := []string{}
	currentToken := ""
	for _, c := range exp {
		if isOperator(string(c)) {
			if currentToken != "" {
				tokens = append(tokens, currentToken)
				currentToken = ""
			}
			tokens = append(tokens, string(c))
		} else {
			currentToken = currentToken + string(c)
		}
	}
	tokens = append(tokens, currentToken)
	return tokens
}

func infixToPostfix(infix []string) []string {
	tokenStack := NewStack()
	postfix := []string{}
	for _, token := range infix {
		if !isOperator(token) {
			postfix = append(postfix, token)
		} else if token == "(" {
			tokenStack.Push(token)
		} else if token == ")" {
			for tokenStack.Top() != "(" {
				postfix = append(postfix, tokenStack.Pop())
			}
			tokenStack.Pop()
		} else {
			for !tokenStack.Empty() && priority(token) < priority(tokenStack.Top()) {
				postfix = append(postfix, tokenStack.Pop())
			}
			tokenStack.Push(token)
		}
	}
	for !tokenStack.Empty() {
		postfix = append(postfix, tokenStack.Pop())
	}
	return postfix
}

func infixToPrefix(infix []string) []string {
	reverse(infix)
	infixLen := len(infix)
	for i := 0; i < infixLen; i++ {
		if infix[i] == "(" {
			infix[i] = ")"
		} else if infix[i] == ")" {
			infix[i] = "("
		}
	}
	prefix := infixToPostfix(infix)
	reverse(prefix)
	return prefix
}
