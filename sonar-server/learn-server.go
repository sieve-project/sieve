package main

import (
	"fmt"
	"log"
	"sync"
	"sync/atomic"
	"time"

	sonar "sonar.client"
)

func NewLearnListener(config map[interface{}]interface{}) *LearnListener {
	server := &learnServer{
		eventCh:                 make(chan eventWrapper, 500),
		eventID:                 -1,
		eventChMap:              sync.Map{},
		notificationCh:       	 make(chan notificationWrapper, 100),
		ongoingReconcileCnt:     0,
		reconcileCntMap:	     map[string]int{},
		recordedEvents:          []eventWrapper{},
	}
	listener := &LearnListener{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

type LearnListener struct {
	Server *learnServer
}

func (l *LearnListener) Echo(request *sonar.EchoRequest, response *sonar.Response) error {
	*response = sonar.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *LearnListener) NotifyLearnBeforeIndexerWrite(request *sonar.NotifyLearnBeforeIndexerWriteRequest, response *sonar.Response) error {
	return l.Server.NotifyLearnBeforeIndexerWrite(request, response)
}

func (l *LearnListener) NotifyLearnBeforeReconcile(request *sonar.NotifyLearnBeforeReconcileRequest, response *sonar.Response) error {
	return l.Server.NotifyLearnBeforeReconcile(request, response)
}

func (l *LearnListener) NotifyLearnAfterReconcile(request *sonar.NotifyLearnAfterReconcileRequest, response *sonar.Response) error {
	return l.Server.NotifyLearnAfterReconcile(request, response)
}

func (l *LearnListener) NotifyLearnSideEffects(request *sonar.NotifyLearnSideEffectsRequest, response *sonar.Response) error {
	return l.Server.NotifyLearnSideEffects(request, response)
}

func (l *LearnListener) NotifyLearnCacheGet(request * sonar.NotifyLearnCacheGetRequest, response *sonar.Response) error {
	return l.Server.NotifyLearnCacheGet(request, response)
}

func (l *LearnListener) NotifyLearnCacheList(request * sonar.NotifyLearnCacheListRequest, response *sonar.Response) error {
	return l.Server.NotifyLearnCacheList(request, response)
}

type eventWrapper struct {
	eventID     int32
	eventType   string
	eventObject string
	eventObjectType string
}

type NotificationType int

const (
	reconcileStart NotificationType = iota
	reconcileFinish
	sideEffect
	cacheRead
)

type notificationWrapper struct {
	ntype NotificationType
	payload string
}

type learnServer struct {
	eventCh                 chan eventWrapper
	eventID                 int32
	eventChMap              sync.Map
	notificationCh          chan notificationWrapper
	ongoingReconcileCnt     int
	reconcileCntMap			map[string]int
	recordedEvents          []eventWrapper
	mu                      sync.Mutex
}

func (s *learnServer) Start() {
	log.Println("start learnServer...")
	go s.coordinatingEvents()
}

func (s *learnServer) NotifyLearnBeforeIndexerWrite(request *sonar.NotifyLearnBeforeIndexerWriteRequest, response *sonar.Response) error {
	// log.Printf("NotifyLearnBeforeIndexerWrite: OperationType: %s and Object: %s\n", request.OperationType, request.Object)
	myID := atomic.AddInt32(&s.eventID, 1)
	myCh := make(chan int32)
	s.eventChMap.Store(myID, myCh)
	ew := eventWrapper{
		eventID:     myID,
		eventType:   request.OperationType,
		eventObject: request.Object,
		eventObjectType: request.ResourceType,
	}
	s.eventCh <- ew
	// log.Printf("my ID is: %d, waiting now...\n", myID)
	<-myCh
	// log.Printf("my ID is: %d, I can go now\n", myID)
	*response = sonar.Response{Message: request.OperationType, Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnBeforeReconcile(request *sonar.NotifyLearnBeforeReconcileRequest, response *sonar.Response) error {
	// log.Printf("NotifyLearnBeforeReconcile\n")
	s.notificationCh <- notificationWrapper{ntype: reconcileStart, payload: request.ControllerName}
	// log.Printf("NotifyLearnBeforeReconcile End\n")
	*response = sonar.Response{Message: "nothing", Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnAfterReconcile(request *sonar.NotifyLearnAfterReconcileRequest, response *sonar.Response) error {
	// log.Printf("NotifyLearnAfterReconcile\n")
	s.notificationCh <- notificationWrapper{ntype: reconcileFinish, payload: request.ControllerName}
	// log.Printf("NotifyLearnAfterReconcile End\n")
	*response = sonar.Response{Message: "nothing", Ok: true}
	return nil
}

func (s *learnServer) extractNameNamespaceRType(Object string) (string, string) {
	objectMap := strToMap(Object)
	name := ""
	namespace := ""
	if _, ok := objectMap["metadata"]; ok {
		if metadataMap, ok := objectMap["metadata"].(map[string]interface{}); ok {
			if _, ok := metadataMap["name"]; ok {
				name = metadataMap["name"].(string)
			}
			if _, ok := metadataMap["namespace"]; ok {
				namespace = metadataMap["namespace"].(string)
			}
		}
	}
	return name, namespace
}

func (s *learnServer) NotifyLearnSideEffects(request *sonar.NotifyLearnSideEffectsRequest, response *sonar.Response) error {
	// log.Printf("NotifyLearnSideEffects: %s %s\n", request.SideEffectType, request.Object)
	rtype := request.ResourceType
	name, namespace := s.extractNameNamespaceRType(request.Object)
	s.notificationCh <- notificationWrapper{ntype: sideEffect, payload: request.SideEffectType + "\t" + rtype + "\t" + namespace + "\t" + name + "\t" + request.Error}
	*response = sonar.Response{Message: request.SideEffectType, Ok: true}
	// log.Printf("NotifyLearnSideEffects: %s %s End\n", request.SideEffectType, request.Object)
	return nil
}

func (s *learnServer) NotifyLearnCacheGet(request *sonar.NotifyLearnCacheGetRequest, response *sonar.Response) error {
	s.notificationCh <- notificationWrapper{ntype: cacheRead, payload: fmt.Sprintf("Get\t%s\t%s\t%s\t%s", request.ResourceType, request.Namespace, request.Name, request.Error)}
	*response = sonar.Response{Message: "Get", Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnCacheList(request *sonar.NotifyLearnCacheListRequest, response *sonar.Response) error {
	s.notificationCh <- notificationWrapper{ntype: cacheRead, payload: fmt.Sprintf("List\t%s\t%s", request.ResourceType, request.Error)}
	*response = sonar.Response{Message: "List", Ok: true}
	return nil
}

func (s *learnServer) coordinatingEvents() {
	for {
		select {
		case <- time.After(time.Second * 3):
			s.allowEvent()
		case nw := <- s.notificationCh:
			switch nw.ntype {
			case reconcileStart:
				s.ongoingReconcileCnt += 1
				if _, ok := s.reconcileCntMap[nw.payload]; ok {
					s.reconcileCntMap[nw.payload] += 1
				} else {
					s.reconcileCntMap[nw.payload] = 0
				}
				log.Printf("[SONAR-START-RECONCILE]\t%s\t%d\n", nw.payload, s.reconcileCntMap[nw.payload])
			case reconcileFinish:
				s.ongoingReconcileCnt -= 1
				if s.ongoingReconcileCnt == 0 {
					s.allowEvent()
				} else if s.ongoingReconcileCnt < 0 {
					log.Fatalf("reconcileCnt cannot be lower than 0: %d\n", s.ongoingReconcileCnt)
				}
				log.Printf("[SONAR-FINISH-RECONCILE]\t%s\t%d\n", nw.payload, s.reconcileCntMap[nw.payload])
			case sideEffect:
				if s.ongoingReconcileCnt > 0 {
					log.Printf("[SONAR-SIDE-EFFECT]\t%s\n", nw.payload)
				}
			case cacheRead:
				log.Printf("[SONAR-CACHE-READ]\t%s", nw.payload)
			}
		}
	}
}

func (s *learnServer) allowEvent() {
	select {
	case ew := <-s.eventCh:
		curID := ew.eventID
		if obj, ok := s.eventChMap.Load(curID); ok {
			log.Printf("[SONAR-EVENT]\t%d\t%s\t%s\t%s\n", ew.eventID, ew.eventType, ew.eventObjectType, ew.eventObject)
			ch := obj.(chan int32)
			ch <- curID
		} else {
			log.Fatal("invalid object in eventCh")
		}
	default:
		log.Println("no event happening")
	}
}
