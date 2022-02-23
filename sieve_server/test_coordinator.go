package main

import (
	"log"

	sieve "sieve.client"
)

type TestCoordinator struct {
	Server *testCoordinator
}

type testCoordinator struct {
	testPlan            *TestPlan
	stateNotificationCh chan TriggerNotification
	blockingChs         map[string]map[string]map[string]chan string
	objectStates        map[string]map[string]map[string]string
	mergedFieldPathMask map[string]map[string]struct{}
	mergedFieldKeyMask  map[string]map[string]struct{}
	stateMachine        *StateMachine
}

func NewTestCoordinator() *TestCoordinator {
	config := getConfig()
	testPlan := parseTestPlan(config)
	mergedFieldPathMask, mergedFieldKeyMask := getMergedMask()
	stateNotificationCh := make(chan TriggerNotification, 500)
	blockingChs := map[string]map[string]map[string]chan string{}
	server := &testCoordinator{
		testPlan:            testPlan,
		stateNotificationCh: stateNotificationCh,
		blockingChs:         blockingChs,
		objectStates:        map[string]map[string]map[string]string{},
		mergedFieldPathMask: mergedFieldPathMask,
		mergedFieldKeyMask:  mergedFieldKeyMask,
		stateMachine:        NewStateMachine(testPlan, stateNotificationCh),
	}
	listener := &TestCoordinator{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

func (l *TestCoordinator) NotifyTestBeforeControllerRecv(request *sieve.NotifyTestBeforeControllerRecvRequest, response *sieve.Response) error {
	return l.Server.NotifyTestBeforeControllerRecv(request, response)
}

func (l *TestCoordinator) NotifyTestAfterControllerRecv(request *sieve.NotifyTestAfterControllerRecvRequest, response *sieve.Response) error {
	return l.Server.NotifyTestAfterControllerRecv(request, response)
}

func (l *TestCoordinator) NotifyTestAfterControllerGet(request *sieve.NotifyTestAfterControllerGetRequest, response *sieve.Response) error {
	return l.Server.NotifyTestAfterControllerGet(request, response)
}

func (l *TestCoordinator) NotifyTestAfterControllerList(request *sieve.NotifyTestAfterControllerListRequest, response *sieve.Response) error {
	return l.Server.NotifyTestAfterControllerList(request, response)
}

func (l *TestCoordinator) NotifyTestAfterControllerWrite(request *sieve.NotifyTestAfterControllerWriteRequest, response *sieve.Response) error {
	return l.Server.NotifyTestAfterControllerWrite(request, response)
}

func (s *testCoordinator) Start() {
	log.Println("start testCoordinator...")
	log.Printf("mergedFieldPathMask:\n%v\n", s.mergedFieldPathMask)
	log.Printf("mergedFieldKeyMask:\n%v\n", s.mergedFieldKeyMask)
	go s.stateMachine.run()
}

func (s *testCoordinator) NotifyTestBeforeControllerRecv(request *sieve.NotifyTestBeforeControllerRecvRequest, response *sieve.Response) error {
	log.Printf("NotifyTestBeforeControllerRecv\t%s\t%s\t%s", request.OperationType, request.ResourceKey, request.Object)
	*response = sieve.Response{Message: "", Ok: true}
	return nil
}

func (s *testCoordinator) NotifyTestAfterControllerRecv(request *sieve.NotifyTestAfterControllerRecvRequest, response *sieve.Response) error {
	log.Printf("NotifyTestAfterControllerRecv\t%s\t%s\t%s", request.OperationType, request.ResourceKey, request.Object)
	*response = sieve.Response{Message: "", Ok: true}
	return nil
}

func (s *testCoordinator) NotifyTestAfterControllerGet(request *sieve.NotifyTestAfterControllerGetRequest, response *sieve.Response) error {
	log.Printf("NotifyTestAfterControllerGet\t%s\t%s\t%s", request.ResourceKey, request.ReconcilerType, request.Object)
	*response = sieve.Response{Message: "", Ok: true}
	return nil
}

func (s *testCoordinator) NotifyTestAfterControllerList(request *sieve.NotifyTestAfterControllerListRequest, response *sieve.Response) error {
	log.Printf("NotifyTestAfterControllerList\t%s\t%s\t%s", request.ResourceType, request.ReconcilerType, request.ObjectList)
	*response = sieve.Response{Message: "", Ok: true}
	return nil
}

func (s *testCoordinator) NotifyTestAfterControllerWrite(request *sieve.NotifyTestAfterControllerWriteRequest, response *sieve.Response) error {
	log.Printf("NotifyTestAfterControllerWrite\t%s\t%s\t%s\t%s", request.WriteType, request.ResourceKey, request.ReconcilerType, request.Object)
	switch request.WriteType {
	case WRITE_CREATE:
		blockingCh := make(chan string)
		notification := &ObjectCreateNotification{
			resourceKey:  request.ResourceKey,
			observedWhen: afterControllerWrite,
			observedBy:   request.ReconcilerType,
			blockingCh:   blockingCh,
		}
		log.Println("send ObjectCreateNotification")
		s.stateNotificationCh <- notification
		<-blockingCh
		log.Println("block is over")
	case WRITE_DELETE:
		blockingCh := make(chan string)
		notification := &ObjectDeleteNotification{
			resourceKey:  request.ResourceKey,
			observedWhen: afterControllerWrite,
			observedBy:   request.ReconcilerType,
			blockingCh:   blockingCh,
		}
		log.Println("send ObjectDeleteNotification")
		s.stateNotificationCh <- notification
		<-blockingCh
		log.Println("block is over")
	default:
		log.Println("do not support other types than create and delete")
	}
	*response = sieve.Response{Message: "", Ok: true}
	return nil
}
