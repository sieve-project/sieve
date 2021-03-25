package main

import (
	"encoding/json"
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
		beforeReconcileCh:       make(chan int32),
		afterReconcileCh:        make(chan int32),
		reconcileCnt:            0,
		shouldRecordSideEffects: false,
		recordedEvents:          []eventWrapper{},
		recordedSideEffects:     []map[string]string{},
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

type eventWrapper struct {
	eventID     int32
	eventType   string
	eventObject string
	eventObjectType string
}

type learnServer struct {
	eventCh                 chan eventWrapper
	eventID                 int32
	eventChMap              sync.Map
	beforeReconcileCh       chan int32
	afterReconcileCh        chan int32
	reconcileCnt            int32
	shouldRecordSideEffects bool
	recordedEvents          []eventWrapper
	recordedSideEffects     []map[string]string
	mu                      sync.Mutex
}

func (s *learnServer) Start() {
	log.Println("start learnServer...")
	go s.coordinatingEvents()
}

func (s *learnServer) NotifyLearnBeforeIndexerWrite(request *sonar.NotifyLearnBeforeIndexerWriteRequest, response *sonar.Response) error {
	log.Printf("NotifyLearnBeforeIndexerWrite: OperationType: %s and Object: %s\n", request.OperationType, request.Object)
	myID := atomic.AddInt32(&s.eventID, 1)
	myCh := make(chan int32)
	s.eventChMap.Store(myID, myCh)
	ew := eventWrapper{
		eventID:     myID,
		eventType:   request.OperationType,
		eventObject: request.Object,
		eventObjectType: request.ResourceType,
	}
	log.Printf("[SONAR-EVENT]\t%d\t%s\t%s\t%s\n", ew.eventID, ew.eventType, ew.eventObjectType, ew.eventObject)
	s.eventCh <- ew
	log.Printf("my ID is: %d, waiting now...\n", myID)
	<-myCh
	log.Printf("my ID is: %d, I can go now\n", myID)
	*response = sonar.Response{Message: request.OperationType, Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnBeforeReconcile(request *sonar.NotifyLearnBeforeReconcileRequest, response *sonar.Response) error {
	log.Printf("NotifyLearnBeforeReconcile\n")
	*response = sonar.Response{Message: "nothing", Ok: true}
	atomic.AddInt32(&s.reconcileCnt, 1)
	s.beforeReconcileCh <- 0
	log.Printf("NotifyLearnBeforeReconcile End\n")
	return nil
}

func (s *learnServer) NotifyLearnAfterReconcile(request *sonar.NotifyLearnAfterReconcileRequest, response *sonar.Response) error {
	log.Printf("NotifyLearnAfterReconcile\n")
	*response = sonar.Response{Message: "nothing", Ok: true}
	atomic.AddInt32(&s.reconcileCnt, -1)
	s.afterReconcileCh <- 0
	log.Printf("NotifyLearnAfterReconcile End\n")
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
			// if _, ok := metadataMap["selfLink"]; ok {
			// 	tokens := strings.Split(metadataMap["selfLink"].(string), "/")
			// 	rtype = tokens[len(tokens) - 2]
			// }
		}
	}
	return name, namespace
}

func (s *learnServer) NotifyLearnSideEffects(request *sonar.NotifyLearnSideEffectsRequest, response *sonar.Response) error {
	log.Printf("NotifyLearnSideEffects: %s %s\n", request.SideEffectType, request.Object)
	rtype := request.ResourceType
	name, namespace := s.extractNameNamespaceRType(request.Object)
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.shouldRecordSideEffects {
		newSideEffect := map[string]string{"etype": request.SideEffectType, "name": name, "namespace": namespace, "rtype": rtype}
		s.recordedSideEffects = append(s.recordedSideEffects, newSideEffect)
	}
	*response = sonar.Response{Message: request.SideEffectType, Ok: true}
	return nil
}

func (s *learnServer) coordinatingEvents() {
	for {
		select {
		case <-time.After(time.Second * 3):
			s.allowEvent()
		case <-s.beforeReconcileCh:
			s.shouldRecordSideEffects = true
		case <-s.afterReconcileCh:
			newVal := atomic.LoadInt32(&s.reconcileCnt)
			if newVal == 0 {
				s.shouldRecordSideEffects = false
				s.mu.Lock()
				if len(s.recordedSideEffects) != 0 {
					for _, recordedEvent := range s.recordedEvents {
						jsonOutput, err := json.Marshal(s.recordedSideEffects)
						if err != nil {
							log.Fatal("error in json")
						}
						log.Printf("[SONAR-RECORD]\t%s\t%d\t%s\t%s\t%s", string(jsonOutput), recordedEvent.eventID, recordedEvent.eventType, recordedEvent.eventObjectType, recordedEvent.eventObject)
					}
				}
				s.recordedEvents = []eventWrapper{}
				s.recordedSideEffects = []map[string]string{}
				s.mu.Unlock()
				s.allowEvent()
			} else if newVal < 0 {
				log.Fatalf("reconcileCnt cannot be lower than 0: %d\n", newVal)
			}
		}
	}
}

func (s *learnServer) allowEvent() {
	select {
	case ew := <-s.eventCh:
		curID := ew.eventID
		log.Printf("timeout! let %d event go\n", curID)
		if obj, ok := s.eventChMap.Load(curID); ok {
			ch := obj.(chan int32)
			ch <- curID
			s.recordedEvents = append(s.recordedEvents, ew)
		} else {
			log.Fatal("invalid object in eventCh")
		}
	default:
		log.Println("no event happening")
	}
}
