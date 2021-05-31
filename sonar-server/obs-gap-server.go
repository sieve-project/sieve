package main

import (
	"log"
	"sync"
	"sync/atomic"

	sonar "sonar.client"
)

func NewObsGapListener(config map[interface{}]interface{}) *ObsGapListener {
	server := &obsGapServer{
		seenPrev:         false,
		eventID:          -1,
		paused:           false,
		pausingReconcile: false,
		crucialCur:       config["ce-diff-current"].(string),
		crucialPrev:      config["ce-diff-previous"].(string),
	}
	server.mutex = &sync.RWMutex{}
	server.cond = sync.NewCond(server.mutex)
	listener := &ObsGapListener{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

type ObsGapListener struct {
	Server *obsGapServer
}

func (l *ObsGapListener) Echo(request *sonar.EchoRequest, response *sonar.Response) error {
	*response = sonar.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *ObsGapListener) NotifyObsGapBeforeIndexerWrite(request *sonar.NotifyObsGapBeforeIndexerWriteRequest, response *sonar.Response) error {
	log.Println("start NotifyObsGapBeforeIndexerWrite...")
	return l.Server.NotifyObsGapBeforeIndexerWrite(request, response)
}

func (l *ObsGapListener) NotifyObsGapAfterIndexerWrite(request *sonar.NotifyObsGapAfterIndexerWriteRequest, response *sonar.Response) error {
	return l.Server.NotifyObsGapAfterIndexerWrite(request, response)
}

func (l *ObsGapListener) NotifyObsGapBeforeReconcile(request *sonar.NotifyObsGapBeforeReconcileRequest, response *sonar.Response) error {
	log.Println("start NotifyObsGapBeforeReconcile...")
	return l.Server.NotifyObsGapBeforeReconcile(request, response)
}

type obsGapServer struct {
	seenPrev         bool
	eventID          int32
	paused           bool
	pausingReconcile bool
	crucialCur       string
	crucialPrev      string
	crucialEvent     eventWrapper
	mutex            *sync.RWMutex
	cond             *sync.Cond
}

func (s *obsGapServer) Start() {
	log.Println("start obsGapServer...")
	// go s.coordinatingEvents()
}

func (s *obsGapServer) shouldPauseReconcile(crucialCurEvent, crucialPrevEvent, currentEvent map[string]interface{}) bool {
	if !s.paused {
		if !s.seenPrev {
			if isCrucial(crucialPrevEvent, currentEvent) && (len(crucialCurEvent) == 0 || !isCrucial(crucialCurEvent, currentEvent)) {
				log.Println("Meet crucialPrevEvent: set seenPrev to true")
				s.seenPrev = true
			}
		} else {
			if isCrucial(crucialCurEvent, currentEvent) && (len(crucialPrevEvent) == 0 || !isCrucial(crucialPrevEvent, currentEvent)) {
				log.Println("Meet crucialCurEvent: set paused to true and start to pause")
				s.paused = true
				return true
			}
		}
	}
	return false
}

func (s *obsGapServer) getEventResourceName(event map[string]interface{}) string {
	metadata := event["metadata"].(map[string]interface{})
	return metadata["name"].(string)
}

func (s *obsGapServer) getEventResourceNamespace(event map[string]interface{}) string {
	metadata := event["metadata"].(map[string]interface{})
	return metadata["namespace"].(string)
}

func (s *obsGapServer) isSameTarget(e1, e2 map[string]interface{}) bool {
	return s.getEventResourceName(e1) == s.getEventResourceName(e2) && s.getEventResourceNamespace(e1) == s.getEventResourceNamespace(e2)
}

// For now, we get an cruial event from API server, we want to see if any later event cancel this one
func (s *obsGapServer) NotifyObsGapBeforeIndexerWrite(request *sonar.NotifyObsGapBeforeIndexerWriteRequest, response *sonar.Response) error {
	eID := atomic.AddInt32(&s.eventID, 1)
	ew := eventWrapper{
		eventID:         eID,
		eventType:       request.OperationType,
		eventObject:     request.Object,
		eventObjectType: request.ResourceType,
	}
	log.Println("NotifyObsGapBeforeIndexerWrite", ew.eventID, ew.eventType, ew.eventObjectType, ew.eventObject)
	currentEvent := strToMap(request.Object)
	crucialCurEvent := strToMap(s.crucialCur)
	crucialPrevEvent := strToMap(s.crucialPrev)
	// We then check for the crucial event
	if s.shouldPauseReconcile(crucialCurEvent, crucialPrevEvent, currentEvent) {
		log.Println("[sonar] should stop any reconcile here until a later cancel event comes")
		s.mutex.Lock()
		s.pausingReconcile = true
		s.crucialEvent = ew
		s.mutex.Unlock()

	}
	*response = sonar.Response{Message: request.OperationType, Ok: true, Number: int(eID)}
	return nil
}

func (s *obsGapServer) NotifyObsGapAfterIndexerWrite(request *sonar.NotifyObsGapAfterIndexerWriteRequest, response *sonar.Response) error {
	// If we are inside pausing, then we check for target event which can cancel the crucial one
	pausingReconcile := false
	s.mutex.RLock()
	pausingReconcile = s.pausingReconcile
	s.mutex.RUnlock()

	log.Println("NotifyObsGapAfterIndexerWrite", pausingReconcile)

	if pausingReconcile {
		currentEvent := strToMap(request.Object)
		crucialEvent := strToMap(s.crucialEvent.eventObject)
		// For now, we simply check for the event which cancel the crucial
		// Later we can use some diff oriented methods (?)
		if request.OperationType == "Deleted" && request.ResourceType == s.crucialEvent.eventObjectType && s.isSameTarget(currentEvent, crucialEvent) {
			// Then we can resume all the reconcile
			log.Println("[sonar] we met the later cancel event, reconcile is resumed")
			s.mutex.Lock()
			s.pausingReconcile = false
			s.cond.Broadcast()
			s.mutex.Unlock()
		}
	}
	*response = sonar.Response{Ok: true}
	return nil
}

func (s *obsGapServer) NotifyObsGapBeforeReconcile(request *sonar.NotifyObsGapBeforeReconcileRequest, response *sonar.Response) error {
	recID := request.ControllerName
	// Fix: use cond variable instead of polling
	// In py part, we can analyze the exisiting of side effect event
	s.mutex.Lock()
	log.Println("NotifyObsGapBeforeReconcile[0/1]", recID, s.pausingReconcile)
	for s.pausingReconcile {
		s.cond.Wait()
	}
	s.mutex.Unlock()
	log.Println("NotifyObsGapBeforeReconcile[1/1]", recID, s.pausingReconcile)
	*response = sonar.Response{Ok: true}
	return nil
}
