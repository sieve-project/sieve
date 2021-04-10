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
		reconcileChMap:		     sync.Map{},
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

func (l *LearnListener) NotifyLearnAfterIndexerWrite(request *sonar.NotifyLearnAfterIndexerWriteRequest, response *sonar.Response) error {
	return l.Server.NotifyLearnAfterIndexerWrite(request, response)
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
	eventApplied
)

type notificationWrapper struct {
	ntype NotificationType
	payload string
}

type learnServer struct {
	eventCh                 chan eventWrapper
	eventID                 int32
	eventChMap              sync.Map
	reconcileChMap          sync.Map
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
	eID := atomic.AddInt32(&s.eventID, 1)
	waitingCh := make(chan int32)
	s.eventChMap.Store(eID, waitingCh)
	ew := eventWrapper{
		eventID:     eID,
		eventType:   request.OperationType,
		eventObject: request.Object,
		eventObjectType: request.ResourceType,
	}
	s.eventCh <- ew
	<- waitingCh
	*response = sonar.Response{Message: request.OperationType, Ok: true, Number: int(eID)}
	return nil
}

func (s *learnServer) NotifyLearnAfterIndexerWrite(request *sonar.NotifyLearnAfterIndexerWriteRequest, response *sonar.Response) error {
	s.notificationCh <- notificationWrapper{ntype: eventApplied, payload: fmt.Sprintf("%d", request.EventID)}
	*response = sonar.Response{Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnBeforeReconcile(request *sonar.NotifyLearnBeforeReconcileRequest, response *sonar.Response) error {
	recID := request.ControllerName
	waitingCh := make(chan int32)
	// use LoadOrStore here because the same controller may have mulitple workers concurrently running reconcile
	// So the same recID may be stored before
	obj, _ := s.reconcileChMap.LoadOrStore(recID, waitingCh);
	waitingCh = obj.(chan int32)
	s.notificationCh <- notificationWrapper{ntype: reconcileStart, payload: recID}
	<- waitingCh
	*response = sonar.Response{Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnAfterReconcile(request *sonar.NotifyLearnAfterReconcileRequest, response *sonar.Response) error {
	s.notificationCh <- notificationWrapper{ntype: reconcileFinish, payload: request.ControllerName}
	*response = sonar.Response{Ok: true}
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
	rtype := request.ResourceType
	name, namespace := s.extractNameNamespaceRType(request.Object)
	s.notificationCh <- notificationWrapper{ntype: sideEffect, payload: request.SideEffectType + "\t" + rtype + "\t" + namespace + "\t" + name + "\t" + request.Error}
	*response = sonar.Response{Message: request.SideEffectType, Ok: true}
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
				if obj, ok := s.reconcileChMap.Load(nw.payload); ok {
					log.Printf("[SONAR-START-RECONCILE]\t%s\t%d\n", nw.payload, s.reconcileCntMap[nw.payload])
					ch := obj.(chan int32)
					ch <- 0
				} else {
					log.Fatal("invalid object in reconcileChMap")
				}
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
			case eventApplied:
				log.Printf("[SONAR-EVENT-APPLIED]\t%s\n", nw.payload)
			case cacheRead:
				log.Printf("[SONAR-CACHE-READ]\t%s\n", nw.payload)
			default:
				log.Fatal("invalid notification type")
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
			log.Fatal("invalid object in eventChMap")
		}
	default:
		log.Println("no event happening")
	}
}
