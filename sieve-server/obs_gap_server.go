package main

import (
	"log"
	"sync"

	sieve "sieve.client"
)

func NewObsGapListener(config map[interface{}]interface{}) *ObsGapListener {
	server := &obsGapServer{
		eventID:          -1,
		pausingReconcile: false,
		diffCurEvent:     strToMap(config["ce-diff-current"].(string)),
		diffPrevEvent:    strToMap(config["ce-diff-previous"].(string)),
		ceName:           config["ce-name"].(string),
		ceNamespace:      config["ce-namespace"].(string),
		ceRtype:          config["ce-rtype"].(string),
		prevEvent:        nil,
		curEvent:         nil,
		reconcilingMutex: &sync.RWMutex{},
	}
	listener := &ObsGapListener{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

type ObsGapListener struct {
	Server *obsGapServer
}

func (l *ObsGapListener) Echo(request *sieve.EchoRequest, response *sieve.Response) error {
	*response = sieve.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *ObsGapListener) NotifyObsGapBeforeIndexerWrite(request *sieve.NotifyObsGapBeforeIndexerWriteRequest, response *sieve.Response) error {
	return l.Server.NotifyObsGapBeforeIndexerWrite(request, response)
}

func (l *ObsGapListener) NotifyObsGapAfterIndexerWrite(request *sieve.NotifyObsGapAfterIndexerWriteRequest, response *sieve.Response) error {
	return l.Server.NotifyObsGapAfterIndexerWrite(request, response)
}

func (l *ObsGapListener) NotifyObsGapBeforeInformerCacheRead(request *sieve.NotifyObsGapBeforeInformerCacheReadRequest, response *sieve.Response) error {
	return l.Server.NotifyObsGapBeforeInformerCacheRead(request, response)
}

func (l *ObsGapListener) NotifyObsGapAfterInformerCacheRead(request *sieve.NotifyObsGapAfterInformerCacheReadRequest, response *sieve.Response) error {
	return l.Server.NotifyObsGapAfterInformerCacheRead(request, response)
}

func (l *ObsGapListener) NotifyObsGapAfterSideEffects(request *sieve.NotifyObsGapAfterSideEffectsRequest, response *sieve.Response) error {
	return l.Server.NotifyObsGapAfterSideEffects(request, response)
}

type obsGapServer struct {
	eventID          int32
	pausingReconcile bool
	diffCurEvent     map[string]interface{}
	diffPrevEvent    map[string]interface{}
	ceName           string
	ceNamespace      string
	ceRtype          string
	reconcilingMutex *sync.RWMutex
	prevEvent        map[string]interface{}
	curEvent         map[string]interface{}
}

func (s *obsGapServer) Start() {
	log.Println("start obsGapServer...")
	log.Printf("target delta: prev: %s\n", mapToStr(s.diffPrevEvent))
	log.Printf("target delta: cur: %s\n", mapToStr(s.diffCurEvent))
}

// For now, we get an cruial event from API server, we want to see if any later event cancel this one
func (s *obsGapServer) NotifyObsGapBeforeIndexerWrite(request *sieve.NotifyObsGapBeforeIndexerWriteRequest, response *sieve.Response) error {
	currentEvent := strToMap(request.Object)
	if !(request.ResourceType == s.ceRtype && isSameObjectServerSide(currentEvent, s.ceNamespace, s.ceName)) {
		log.Fatalf("encounter unexpected object: %s %s", request.ResourceType, request.Object)
	}
	log.Println("NotifyObsGapBeforeIndexerWrite", request.OperationType, request.ResourceType, request.Object)
	s.prevEvent = s.curEvent
	s.curEvent = currentEvent
	if findTargetDiff(s.prevEvent, s.curEvent, s.diffPrevEvent, s.diffCurEvent, false) {
		startObsGapInjection()
		log.Println("[sieve] should stop any reconcile here until a later cancel event comes")
		s.reconcilingMutex.Lock()
		s.pausingReconcile = true
		log.Println("[sieve] start to pause")
	}
	*response = sieve.Response{Message: request.OperationType, Ok: true}
	return nil
}

func (s *obsGapServer) NotifyObsGapAfterIndexerWrite(request *sieve.NotifyObsGapAfterIndexerWriteRequest, response *sieve.Response) error {
	currentEvent := strToMap(request.Object)
	if !(request.ResourceType == s.ceRtype && isSameObjectServerSide(currentEvent, s.ceNamespace, s.ceName)) {
		log.Fatalf("encounter unexpected object: %s %s", request.ResourceType, request.Object)
	}
	// If we are inside pausing, then we check for target event which can cancel the crucial one
	log.Println("NotifyObsGapAfterIndexerWrite", s.pausingReconcile)
	if s.pausingReconcile {
		if request.OperationType == "Deleted" || conflictingEventAsMap(s.diffCurEvent, currentEvent) {
			// TODO: we should also consider the corner case where s.diffCurEvent == {}
			log.Printf("[sieve] we met the cancel event %s, reconcile is resumed\n", request.OperationType)
			log.Println("NotifyObsGapAfterIndexerWrite", request.OperationType, request.ResourceType, request.Object)
			s.pausingReconcile = false
			s.reconcilingMutex.Unlock()
			finishObsGapInjection()
		}
	}
	*response = sieve.Response{Ok: true}
	return nil
}

func (s *obsGapServer) NotifyObsGapBeforeInformerCacheRead(request *sieve.NotifyObsGapBeforeInformerCacheReadRequest, response *sieve.Response) error {
	if request.OperationType == "Get" {
		if !(request.ResourceType == s.ceRtype && request.Name == s.ceName && request.Namespace == s.ceNamespace) {
			log.Fatalf("encounter unexpected object: %s %s %s", request.ResourceType, request.Namespace, request.Name)
		}
	} else {
		if !(request.ResourceType == s.ceRtype+"list") {
			log.Fatalf("encounter unexpected object: %s", request.ResourceType)
		}
	}
	log.Println("NotifyObsGapBeforeInformerCacheRead[0/1]", s.pausingReconcile)
	s.reconcilingMutex.Lock()
	log.Println("NotifyObsGapBeforeInformerCacheRead[1/1]", s.pausingReconcile)
	*response = sieve.Response{Ok: true}
	return nil
}

func (s *obsGapServer) NotifyObsGapAfterInformerCacheRead(request *sieve.NotifyObsGapAfterInformerCacheReadRequest, response *sieve.Response) error {
	if request.OperationType == "Get" {
		if !(request.ResourceType == s.ceRtype && request.Name == s.ceName && request.Namespace == s.ceNamespace) {
			log.Fatalf("encounter unexpected object: %s %s %s", request.ResourceType, request.Namespace, request.Name)
		}
	} else {
		if !(request.ResourceType == s.ceRtype+"list") {
			log.Fatalf("encounter unexpected object: %s", request.ResourceType)
		}
	}
	log.Println("NotifyObsGapAfterInformerCacheRead")
	s.reconcilingMutex.Unlock()
	*response = sieve.Response{Ok: true}
	return nil
}

func (s *obsGapServer) NotifyObsGapAfterSideEffects(request *sieve.NotifyObsGapAfterSideEffectsRequest, response *sieve.Response) error {
	log.Printf("[SIEVE-AFTER-SIDE-EFFECT]\t%d\t%s\t%s\t%s\t%s\n", request.SideEffectID, request.SideEffectType, request.ResourceType, request.Error, request.Object)
	*response = sieve.Response{Message: request.SideEffectType, Ok: true}
	return nil
}
