package main

type Stack struct {
	elements []string
	topPtr   int
}

func NewStack() *Stack {
	return &Stack{
		elements: []string{},
		topPtr:   -1,
	}
}

func (s *Stack) Empty() bool {
	return s.topPtr == -1
}

func (s *Stack) Top() string {
	return s.elements[s.topPtr]
}

func (s *Stack) Push(element string) {
	if len(s.elements) > s.topPtr+1 {
		s.elements[s.topPtr+1] = element
	} else {
		s.elements = append(s.elements, element)
	}
	s.topPtr += 1
}

func (s *Stack) Pop() string {
	ret := s.elements[s.topPtr]
	s.topPtr -= 1
	return ret
}
