package main

import (
	"fmt"
	"runtime/debug"
	"testing"
)

func TestStack(t *testing.T) {
	fmt.Println(string(debug.Stack()))
}
