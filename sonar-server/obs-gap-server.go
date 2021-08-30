package main

import (
	"log"
	"sync"
	"sync/atomic"
	"time"

	sonar "sonar.client"
)

func NewObsGapListener(config map[interface{}]interface{}) *ObsGapListener {
	server := &obsGapServer{
		seenPrev:           false,
		eventID:            -1,
		paused:             false,
		pausingReconcile:   false,
		crucialCur:         config["ce-diff-current"].(string),
		crucialPrev:        config["ce-diff-previous"].(string),
		ceName:             config["ce-name"].(string),
		ceNamespace:        config["ce-namespace"].(string),
		ceRtype:            config["ce-rtype"].(string),
		pausedReconcileCnt: 0,
	}
	server.mutex = &sync.RWMutex{}
	server.reconcilingMutex = &sync.RWMutex{}
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

type eventWrapper struct {
	eventID         int32
	eventType       string
	eventObject     string
	eventObjectType string
}

func (l *ObsGapListener) Echo(request *sonar.EchoRequest, response *sonar.Response) error {
	*response = sonar.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *ObsGapListener) NotifyObsGapBeforeIndexerWrite(request *sonar.NotifyObsGapBeforeIndexerWriteRequest, response *sonar.Response) error {
	return l.Server.NotifyObsGapBeforeIndexerWrite(request, response)
}

func (l *ObsGapListener) NotifyObsGapAfterIndexerWrite(request *sonar.NotifyObsGapAfterIndexerWriteRequest, response *sonar.Response) error {
	return l.Server.NotifyObsGapAfterIndexerWrite(request, response)
}

func (l *ObsGapListener) NotifyObsGapBeforeReconcile(request *sonar.NotifyObsGapBeforeReconcileRequest, response *sonar.Response) error {
	return l.Server.NotifyObsGapBeforeReconcile(request, response)
}

func (l *ObsGapListener) NotifyObsGapAfterReconcile(request *sonar.NotifyObsGapAfterReconcileRequest, response *sonar.Response) error {
	return l.Server.NotifyObsGapAfterReconcile(request, response)
}

func (l *ObsGapListener) NotifyObsGapSideEffects(request *sonar.NotifyObsGapSideEffectsRequest, response *sonar.Response) error {
	return l.Server.NotifyObsGapSideEffects(request, response)
}

type obsGapServer struct {
	seenPrev           bool
	eventID            int32
	paused             bool
	pausingReconcile   bool
	crucialCur         string
	crucialPrev        string
	ceName             string
	ceNamespace        string
	ceRtype            string
	crucialEvent       eventWrapper
	mutex              *sync.RWMutex
	reconcilingMutex   *sync.RWMutex
	cond               *sync.Cond
	pausedReconcileCnt int32
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

func getEventResourceName(event map[string]interface{}) string {
	if event["metadata"] != nil {
		metadata := event["metadata"].(map[string]interface{})
		return metadata["name"].(string)
	} else {
		return event["name"].(string)
	}
}

func getEventResourceNamespace(event map[string]interface{}) string {
	if event["metadata"] != nil {
		metadata := event["metadata"].(map[string]interface{})
		return metadata["namespace"].(string)
	} else {
		return event["namespace"].(string)
	}
}

func (s *obsGapServer) isSameTarget(currentEvent map[string]interface{}) bool {
	return getEventResourceName(currentEvent) == s.ceName && getEventResourceNamespace(currentEvent) == s.ceNamespace
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
	if ew.eventObjectType == s.ceRtype && s.isSameTarget(currentEvent) && s.shouldPauseReconcile(crucialCurEvent, crucialPrevEvent, currentEvent) {
		s.reconcilingMutex.Lock()
		log.Println("[sonar] should stop any reconcile here until a later cancel event comes")
		s.mutex.Lock()
		s.pausingReconcile = true
		s.crucialEvent = ew
		s.mutex.Unlock()
		s.reconcilingMutex.Unlock()

		go func() {
			time.Sleep(time.Second * 30)
			s.mutex.Lock()
			if s.pausingReconcile {
				s.pausingReconcile = false
				s.cond.Broadcast()
				log.Println("[sonar] we met the timeout for reconcile pausing, reconcile is resumed", s.pausedReconcileCnt)
			}
			s.mutex.Unlock()
		}()
	}
	*response = sonar.Response{Message: request.OperationType, Ok: true, Number: int(eID)}
	return nil
}

func cancelEventList(crucialEvent, currentEvent []interface{}) bool {
	if len(currentEvent) < len(crucialEvent) {
		return true
	}
	for i, val := range crucialEvent {
		switch v := val.(type) {
		case int64:
			if e, ok := currentEvent[i].(int64); ok {
				if v != e {
					log.Println("cancel event", v, e)
					return true
				}
			}
		case float64:
			if e, ok := currentEvent[i].(float64); ok {
				if v != e {
					log.Println("cancel event", v, e)
					return true
				}
			}
		case bool:
			if e, ok := currentEvent[i].(bool); ok {
				if v != e {
					log.Println("cancel event", v, e)
					return true
				}
			}
		case string:
			if v == "SIEVE-NON-NIL" || v == "SIEVE-SKIP" {
				continue
			} else if e, ok := currentEvent[i].(string); ok {
				if v != e {
					log.Println("cancel event", v, e)
					return true
				}
			}
		case map[string]interface{}:
			if e, ok := currentEvent[i].(map[string]interface{}); ok {
				if cancelEvent(v, e) {
					log.Println("cancel event", v, e)
					return true
				}
			}
		default:
			log.Printf("Unsupported type: %v %T\n", v, v)
		}
	}
	return false
}

func cancelEvent(crucialEvent, currentEvent map[string]interface{}) bool {
	for key, val := range crucialEvent {
		if _, ok := currentEvent[key]; !ok {
			log.Println("cancel event, not exist", key)
			return true
		}
		switch v := val.(type) {
		case int64:
			if e, ok := currentEvent[key].(int64); ok {
				if v != e {
					log.Println("cancel event", key)
					return true
				}
			}
		case float64:
			if e, ok := currentEvent[key].(float64); ok {
				if v != e {
					log.Println("cancel event", key)
					return true
				}
			}
		case bool:
			if e, ok := currentEvent[key].(bool); ok {
				if v != e {
					log.Println("cancel event", key)
					return true
				}
			}
		case string:
			if v == "SIEVE-NON-NIL" {
				continue
			} else if e, ok := currentEvent[key].(string); ok {
				if v != e {
					log.Println("cancel event", key)
					return true
				}
			}
		case map[string]interface{}:
			if e, ok := currentEvent[key].(map[string]interface{}); ok {
				if cancelEvent(v, e) {
					log.Println("cancel event", key)
					return true
				}
			}
		case []interface{}:
			if e, ok := currentEvent[key].([]interface{}); ok {
				if cancelEventList(v, e) {
					log.Println("cancel event", key)
					return true
				}
			}

		default:
			log.Printf("Unsupported type: %v %T, key: %s\n", v, v, key)
		}
	}
	return false
}

func (s *obsGapServer) NotifyObsGapAfterIndexerWrite(request *sonar.NotifyObsGapAfterIndexerWriteRequest, response *sonar.Response) error {
	// If we are inside pausing, then we check for target event which can cancel the crucial one
	pausingReconcile := false
	s.mutex.RLock()
	pausingReconcile = s.pausingReconcile
	s.mutex.RUnlock()

	log.Println("NotifyObsGapAfterIndexerWrite", pausingReconcile, "pausedReconcileCnt", s.pausedReconcileCnt)

	if pausingReconcile {
		currentEvent := strToMap(request.Object)
		crucialEvent := strToMap(s.crucialEvent.eventObject)
		// For now, we simply check for the event which cancel the crucial
		// Later we can use some diff oriented methods (?)
		if request.OperationType == "Deleted" && request.ResourceType == s.crucialEvent.eventObjectType && s.isSameTarget(currentEvent) {
			// Then we can resume all the reconcile
			log.Printf("[sonar] we met the later cancel event %s, reconcile is resumed, paused cnt: %d\n", request.OperationType, s.pausedReconcileCnt)
			log.Println("NotifyObsGapAfterIndexerWrite", request.OperationType, request.ResourceType, request.Object)
			s.mutex.Lock()
			s.pausingReconcile = false
			s.cond.Broadcast()
			s.mutex.Unlock()
		} else if request.ResourceType == s.crucialEvent.eventObjectType && s.isSameTarget(currentEvent) {
			// We also propose a diff based method for the cancel
			if cancelEvent(crucialEvent, currentEvent) {
				log.Printf("[sonar] we met the later cancel event %s, reconcile is resumed, paused cnt: %d\n", request.OperationType, s.pausedReconcileCnt)
				log.Println("NotifyObsGapAfterIndexerWrite", request.OperationType, request.ResourceType, request.Object)
				time.Sleep(time.Second * 30)
				log.Println("Go now!")
				s.mutex.Lock()
				s.pausingReconcile = false
				s.cond.Broadcast()
				s.mutex.Unlock()
			}
		}

	}
	*response = sonar.Response{Ok: true}
	return nil
}

func (s *obsGapServer) NotifyObsGapBeforeReconcile(request *sonar.NotifyObsGapBeforeReconcileRequest, response *sonar.Response) error {
	s.reconcilingMutex.Lock()
	recID := request.ControllerName
	// Fix: use cond variable instead of polling
	// In py part, we can analyze the exisiting of side effect event
	s.mutex.Lock()
	log.Println("NotifyObsGapBeforeReconcile[0/1]", recID, s.pausingReconcile)
	if s.pausingReconcile {
		atomic.AddInt32(&s.pausedReconcileCnt, 1)
	}
	for s.pausingReconcile {
		s.cond.Wait()
	}
	s.mutex.Unlock()
	log.Println("NotifyObsGapBeforeReconcile[1/1]", recID, s.pausingReconcile)
	*response = sonar.Response{Ok: true}
	return nil
}

func (s *obsGapServer) NotifyObsGapAfterReconcile(request *sonar.NotifyObsGapAfterReconcileRequest, response *sonar.Response) error {
	recID := request.ControllerName
	log.Println("NotifyObsGapAfterReconcile", recID)
	*response = sonar.Response{Ok: true}
	s.reconcilingMutex.Unlock()
	return nil
}

func (s *obsGapServer) NotifyObsGapSideEffects(request *sonar.NotifyObsGapSideEffectsRequest, response *sonar.Response) error {
	name, namespace := extractNameNamespace(request.Object)
	log.Printf("[SONAR-SIDE-EFFECT]\t%s\t%s\t%s\t%s\t%s\n", request.SideEffectType, request.ResourceType, namespace, name, request.Error)
	*response = sonar.Response{Message: request.SideEffectType, Ok: true}
	return nil
}
