package main

import (
	"log"
	"time"
	"sync/atomic"
	"sync"
	"encoding/json"

	sonar "sonar.client/pkg/sonar"
)

func NewLearnListener(config map[interface{}]interface{}) *LearnListener {
	server := &learnServer{
		eventCh:  	make(chan eventWrapper, 500),
		eventID: 	-1,
		eventChMap: sync.Map{},
		beforeReconcileCh: make(chan int32),
		afterReconcileCh: make(chan int32),
		reconcileCnt: 0,
		shouldRecordSideEffects: false,
		recordedEvents: []eventWrapper{},
		recordedSideEffects: []string{},
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

func (l *LearnListener) NotifyBeforeIndexerWrite(request *sonar.NotifyLearnBeforeIndexerWriteRequest, response *sonar.Response) error {
	return l.Server.NotifyBeforeIndexerWrite(request, response)
}

func (l *LearnListener) NotifyBeforeReconcile(request *sonar.NotifyLearnBeforeReconcileRequest, response *sonar.Response) error {
	return l.Server.NotifyBeforeReconcile(request, response)
}

func (l *LearnListener) NotifyAfterReconcile(request *sonar.NotifyLearnAfterReconcileRequest, response *sonar.Response) error {
	return l.Server.NotifyAfterReconcile(request, response)
}

func (l *LearnListener) NotifySideEffects(request *sonar.NotifyLearnSideEffectsRequest, response *sonar.Response) error {
	return l.Server.NotifySideEffects(request, response)
}

type eventWrapper struct {
	eventID int32
	eventType string
	eventObject string
}

type learnServer struct {
	eventCh chan eventWrapper
	eventID int32
	eventChMap sync.Map
	beforeReconcileCh chan int32
	afterReconcileCh chan int32
	reconcileCnt int32
	shouldRecordSideEffects bool
	recordedEvents []eventWrapper
	recordedSideEffects []string
	mu sync.Mutex
}

func (s *learnServer) Start() {
	log.Println("start learnServer...")
	go s.coordinatingEvents()
}

func (s *learnServer) NotifyBeforeIndexerWrite(request *sonar.NotifyLearnBeforeIndexerWriteRequest, response *sonar.Response) error {
	log.Printf("NotifyBeforeIndexerWrite: OperationType: %s and Object: %s\n", request.OperationType, request.Object)
	myID := atomic.AddInt32(&s.eventID, 1)
	myCh := make(chan int32)
	s.eventChMap.Store(myID, myCh)
	ew := eventWrapper {
		eventID: myID,
		eventType: request.OperationType,
		eventObject: request.Object,
	}
	s.eventCh <- ew
	log.Printf("my ID is: %d, waiting now...\n", myID)
	<-myCh
	log.Printf("my ID is: %d, I can go now\n", myID)
	*response = sonar.Response{Message: request.OperationType, Ok: true}
	return nil
}

func (s *learnServer) NotifyBeforeReconcile(request *sonar.NotifyLearnBeforeReconcileRequest, response *sonar.Response) error {
	log.Printf("NotifyBeforeReconcile\n")
	*response = sonar.Response{Message: "nothing", Ok: true}
	atomic.AddInt32(&s.reconcileCnt, 1)
	s.beforeReconcileCh <- 0
	return nil
}

func (s *learnServer) NotifyAfterReconcile(request *sonar.NotifyLearnAfterReconcileRequest, response *sonar.Response) error {
	log.Printf("NotifyAfterReconcile\n")
	*response = sonar.Response{Message: "nothing", Ok: true}
	atomic.AddInt32(&s.reconcileCnt, -1)
	s.afterReconcileCh <- 0
	return nil
}

func (s *learnServer) NotifySideEffects(request *sonar.NotifyLearnSideEffectsRequest, response *sonar.Response) error {
	log.Printf("NotifySideEffects: %s\n", request.SideEffectType)
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.shouldRecordSideEffects {
		s.recordedSideEffects = append(s.recordedSideEffects, request.SideEffectType)
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
						log.Printf("[LEARN]\t%s\t%s\t%s", string(jsonOutput), recordedEvent.eventType, recordedEvent.eventObject)
					}
				}
				s.recordedEvents = []eventWrapper{}
				s.recordedSideEffects = []string{}
				s.mu.Unlock()
				s.allowEvent()
			} else if newVal < 0 {
				log.Fatalf("reconcileCnt cannot be lower than 0: %d\n", newVal)
			}
		}
	}
}

func (s *learnServer) allowEvent() {
	ew := <-s.eventCh
	curID := ew.eventID
	if obj, ok := s.eventChMap.Load(curID); ok {
		ch := obj.(chan int32)
		ch <- curID
		s.recordedEvents = append(s.recordedEvents, ew)
	} else {
		log.Fatal("invalid object in eventCh")
	}
}
