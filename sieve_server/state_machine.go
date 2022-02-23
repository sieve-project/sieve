package main

type StateMachine struct {
	states    []*Action
	nextState int
}

func NewStateMachine(testPlan *TestPlan) *StateMachine {
	return &StateMachine{
		states:    testPlan.actions,
		nextState: 0,
	}
}
