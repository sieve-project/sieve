package main

import (
	"log"
	"sync"

	sieve "sieve.client"
)

type TestCoordinator struct {
	Server *testCoordinator
}

type testCoordinator struct {
	testPlan            *TestPlan
	actionConext        *ActionContext
	stateNotificationCh chan TriggerNotification
	blockingChs         map[string]map[string]map[string]chan string
	objectStates        map[string]map[string]map[string]map[string]interface{}
	mergedFieldPathMask map[string]map[string]struct{}
	mergedFieldKeyMask  map[string]map[string]struct{}
	stateMachine        *StateMachine
}

func NewTestCoordinator() *TestCoordinator {
	config := getConfig()
	testPlan := parseTestPlan(config)
	actionConext := &ActionContext{
		namespace:          "default",
		leadingAPIServer:   "kind-control-plane",
		followingAPIServer: "kind-control-plane3",
		controllerLock:     &sync.Mutex{},
		apiserverLocks:     map[string]*sync.Mutex{},
	}
	mergedFieldPathMask, mergedFieldKeyMask := getMergedMask()
	stateNotificationCh := make(chan TriggerNotification, 500)
	blockingChs := map[string]map[string]map[string]chan string{}
	server := &testCoordinator{
		testPlan:            testPlan,
		actionConext:        actionConext,
		stateNotificationCh: stateNotificationCh,
		blockingChs:         blockingChs,
		objectStates:        map[string]map[string]map[string]map[string]interface{}{},
		mergedFieldPathMask: mergedFieldPathMask,
		mergedFieldKeyMask:  mergedFieldKeyMask,
		stateMachine:        NewStateMachine(testPlan, stateNotificationCh, actionConext),
	}
	listener := &TestCoordinator{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

func (l *TestCoordinator) NotifyTestBeforeAPIServerRecv(request *sieve.NotifyTestBeforeAPIServerRecvRequest, response *sieve.Response) error {
	return l.Server.NotifyTestBeforeAPIServerRecv(request, response)
}

func (l *TestCoordinator) NotifyTestAfterAPIServerRecv(request *sieve.NotifyTestAfterAPIServerRecvRequest, response *sieve.Response) error {
	return l.Server.NotifyTestAfterAPIServerRecv(request, response)
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

func (s *testCoordinator) SendObjectCreateNotificationAndBlock(handlerName, resourceKey, observedWhen, observedBy string) {
	blockingCh := make(chan string)
	notification := &ObjectCreateNotification{
		resourceKey:  resourceKey,
		observedWhen: observedWhen,
		observedBy:   observedBy,
		blockingCh:   blockingCh,
	}
	log.Printf("%s: send ObjectCreateNotification\n", handlerName)
	s.stateNotificationCh <- notification
	<-blockingCh
	log.Printf("%s: block over for ObjectCreateNotification\n", handlerName)
}

func (s *testCoordinator) SendObjectDeleteNotificationAndBlock(handlerName, resourceKey, observedWhen, observedBy string) {
	blockingCh := make(chan string)
	notification := &ObjectDeleteNotification{
		resourceKey:  resourceKey,
		observedWhen: observedWhen,
		observedBy:   observedBy,
		blockingCh:   blockingCh,
	}
	log.Printf("%s: send ObjectDeleteNotification\n", handlerName)
	s.stateNotificationCh <- notification
	<-blockingCh
	log.Printf("%s: block over for ObjectDeleteNotification\n", handlerName)
}

func (s *testCoordinator) SendObjectUpdateNotificationAndBlock(handlerName, resourceKey, observedWhen, observedBy string, prevState, curState map[string]interface{}) {
	blockingCh := make(chan string)
	notification := &ObjectUpdateNotification{
		resourceKey:   resourceKey,
		observedWhen:  observedWhen,
		observedBy:    observedBy,
		prevState:     prevState,
		curState:      curState,
		fieldKeyMask:  s.mergedFieldKeyMask[resourceKey],
		fieldPathMask: s.mergedFieldPathMask[resourceKey],
		blockingCh:    blockingCh,
	}
	log.Printf("%s: send ObjectUpdateNotification\n", handlerName)
	s.stateNotificationCh <- notification
	<-blockingCh
	log.Printf("%s: block over for ObjectUpdateNotification\n", handlerName)
}

func (s *testCoordinator) InitializeObjectStatesEntry(observedBy, observedWhen, resourceKey string) {
	if _, ok := s.objectStates[observedBy]; !ok {
		s.objectStates[observedBy] = map[string]map[string]map[string]interface{}{}
	}
	if _, ok := s.objectStates[observedBy][observedWhen]; !ok {
		s.objectStates[observedBy][observedWhen] = map[string]map[string]interface{}{}
	}
	if _, ok := s.objectStates[observedBy][observedWhen][resourceKey]; !ok {
		s.objectStates[observedBy][observedWhen][resourceKey] = map[string]interface{}{}
	}
}

func (s *testCoordinator) NotifyTestBeforeAPIServerRecv(request *sieve.NotifyTestBeforeAPIServerRecvRequest, response *sieve.Response) error {
	handlerName := "NotifyTestBeforeAPIServerRecv"
	log.Printf("%s\t%s\t%s\t%s\t%s", request.APIServerHostname, handlerName, request.OperationType, request.ResourceKey, request.Object)
	switch request.OperationType {
	case API_ADDED:
		s.SendObjectCreateNotificationAndBlock(handlerName, request.ResourceKey, beforeAPIServerRecv, request.APIServerHostname)
	case API_DELETED:
		s.SendObjectDeleteNotificationAndBlock(handlerName, request.ResourceKey, beforeAPIServerRecv, request.APIServerHostname)
	default:
		log.Println("do not support other types than create and delete")
	}
	*response = sieve.Response{Message: "", Ok: true}
	return nil
}

func (s *testCoordinator) NotifyTestAfterAPIServerRecv(request *sieve.NotifyTestAfterAPIServerRecvRequest, response *sieve.Response) error {
	handlerName := "NotifyTestAfterAPIServerRecv"
	log.Printf("%s\t%s\t%s\t%s\t%s", request.APIServerHostname, handlerName, request.OperationType, request.ResourceKey, request.Object)
	switch request.OperationType {
	case API_ADDED:
		s.SendObjectCreateNotificationAndBlock(handlerName, request.ResourceKey, afterAPIServerRecv, request.APIServerHostname)
	case API_DELETED:
		s.SendObjectDeleteNotificationAndBlock(handlerName, request.ResourceKey, afterAPIServerRecv, request.APIServerHostname)
	default:
		log.Println("do not support other types than create and delete")
	}
	*response = sieve.Response{Message: "", Ok: true}
	return nil
}

func (s *testCoordinator) NotifyTestBeforeControllerRecv(request *sieve.NotifyTestBeforeControllerRecvRequest, response *sieve.Response) error {
	handlerName := "NotifyTestBeforeControllerRecv"
	log.Printf("%s\t%s\t%s\t%s", handlerName, request.OperationType, request.ResourceKey, request.Object)
	switch request.OperationType {
	case HEAR_ADDED:
		s.SendObjectCreateNotificationAndBlock(handlerName, request.ResourceKey, beforeControllerRecv, "")
	case HEAR_DELETED:
		s.SendObjectDeleteNotificationAndBlock(handlerName, request.ResourceKey, beforeControllerRecv, "")
	default:
		log.Println("do not support other types than create and delete")
	}
	*response = sieve.Response{Message: "", Ok: true}
	return nil
}

func (s *testCoordinator) NotifyTestAfterControllerRecv(request *sieve.NotifyTestAfterControllerRecvRequest, response *sieve.Response) error {
	handlerName := "NotifyTestAfterControllerRecv"
	log.Printf("%s\t%s\t%s\t%s", handlerName, request.OperationType, request.ResourceKey, request.Object)
	switch request.OperationType {
	case HEAR_ADDED:
		s.SendObjectCreateNotificationAndBlock(handlerName, request.ResourceKey, afterControllerRecv, "")
	case HEAR_DELETED:
		s.SendObjectDeleteNotificationAndBlock(handlerName, request.ResourceKey, afterControllerRecv, "")
	default:
		log.Println("do not support other types than create and delete")
	}
	*response = sieve.Response{Message: "", Ok: true}
	return nil
}

func (s *testCoordinator) NotifyTestAfterControllerGet(request *sieve.NotifyTestAfterControllerGetRequest, response *sieve.Response) error {
	log.Printf("NotifyTestAfterControllerGet\t%s\t%s\t%s", request.ResourceKey, request.ReconcilerType, request.Object)
	s.InitializeObjectStatesEntry(request.ReconcilerType, afterControllerWrite, request.ResourceKey)
	// need lock here
	objectState := strToMap(request.Object)
	trimKindApiversion(objectState)
	s.objectStates[request.ReconcilerType][afterControllerWrite][request.ResourceKey] = objectState
	*response = sieve.Response{Message: "", Ok: true}
	return nil
}

func (s *testCoordinator) NotifyTestAfterControllerList(request *sieve.NotifyTestAfterControllerListRequest, response *sieve.Response) error {
	log.Printf("NotifyTestAfterControllerList\t%s\t%s\t%s", request.ResourceType, request.ReconcilerType, request.ObjectList)
	// need lock here
	objects := strToMap(request.ObjectList)["items"].([]interface{})
	for _, object := range objects {
		objectState := object.(map[string]interface{})
		name, namespace := extractNameNamespaceFromObjMap(objectState)
		resourceKey := generateResourceKey(request.ResourceType, namespace, name)
		trimKindApiversion(objectState)
		s.objectStates[request.ReconcilerType][afterControllerWrite][resourceKey] = objectState
	}
	*response = sieve.Response{Message: "", Ok: true}
	return nil
}

func (s *testCoordinator) NotifyTestAfterControllerWrite(request *sieve.NotifyTestAfterControllerWriteRequest, response *sieve.Response) error {
	handlerName := "NotifyTestAfterControllerWrite"
	log.Printf("%s\t%s\t%s\t%s\t%s", handlerName, request.WriteType, request.ResourceKey, request.ReconcilerType, request.Object)
	s.InitializeObjectStatesEntry(request.ReconcilerType, afterControllerWrite, request.ResourceKey)
	prevObjectState := s.objectStates[request.ReconcilerType][afterControllerWrite][request.ResourceKey]
	switch request.WriteType {
	case WRITE_CREATE:
		s.SendObjectCreateNotificationAndBlock(handlerName, request.ResourceKey, afterControllerWrite, request.ReconcilerType)
	case WRITE_UPDATE, WRITE_PATCH, WRITE_STATUS_UPDATE, WRITE_STATUS_PATCH:
		curObjectState := strToMap(request.Object)
		trimKindApiversion(curObjectState)
		s.SendObjectUpdateNotificationAndBlock(handlerName, request.ResourceKey, afterControllerWrite, request.ReconcilerType, prevObjectState, curObjectState)
	case WRITE_DELETE:
		s.SendObjectDeleteNotificationAndBlock(handlerName, request.ResourceKey, afterControllerWrite, request.ReconcilerType)
	default:
		log.Println("do not support other types than create and delete")
	}
	*response = sieve.Response{Message: "", Ok: true}
	return nil
}
