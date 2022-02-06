package main

import (
	"log"
	"sync"

	sieve "sieve.client"
)

func NewUnobsrStateListener(config map[interface{}]interface{}, learnedFieldPathMask, configuredFieldPathMask, configuredFieldKeyMask map[string][]string) *UnobsrStateListener {
	maskedKeysSet, maskedPathsSet := mergeAndRefineMask(config["ce-rtype"].(string), config["ce-namespace"].(string), config["ce-name"].(string), learnedFieldPathMask, configuredFieldPathMask, configuredFieldKeyMask)
	server := &unobsrStateServer{
		eventID:          -1,
		pausingReconcile: false,
		diffCurEvent:     strToMap(config["ce-diff-current"].(string)),
		diffPrevEvent:    strToMap(config["ce-diff-previous"].(string)),
		ceName:           config["ce-name"].(string),
		ceNamespace:      config["ce-namespace"].(string),
		ceRtype:          config["ce-rtype"].(string),
		ceEtype:          config["ce-etype-current"].(string),
		eventCounter:     strToInt(config["ce-counter"].(string)),
		prevEvent:        make(map[string]interface{}),
		curEvent:         make(map[string]interface{}),
		reconcilingMutex: &sync.RWMutex{},
		maskedKeysSet:    maskedKeysSet,
		maskedPathsSet:   maskedPathsSet,
	}
	listener := &UnobsrStateListener{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

type UnobsrStateListener struct {
	Server *unobsrStateServer
}

func (l *UnobsrStateListener) Echo(request *sieve.EchoRequest, response *sieve.Response) error {
	*response = sieve.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *UnobsrStateListener) NotifyUnobsrStateBeforeIndexerWrite(request *sieve.NotifyUnobsrStateBeforeIndexerWriteRequest, response *sieve.Response) error {
	return l.Server.NotifyUnobsrStateBeforeIndexerWrite(request, response)
}

func (l *UnobsrStateListener) NotifyUnobsrStateAfterIndexerWrite(request *sieve.NotifyUnobsrStateAfterIndexerWriteRequest, response *sieve.Response) error {
	return l.Server.NotifyUnobsrStateAfterIndexerWrite(request, response)
}

func (l *UnobsrStateListener) NotifyUnobsrStateBeforeInformerCacheRead(request *sieve.NotifyUnobsrStateBeforeInformerCacheReadRequest, response *sieve.Response) error {
	return l.Server.NotifyUnobsrStateBeforeInformerCacheRead(request, response)
}

func (l *UnobsrStateListener) NotifyUnobsrStateAfterInformerCacheRead(request *sieve.NotifyUnobsrStateAfterInformerCacheReadRequest, response *sieve.Response) error {
	return l.Server.NotifyUnobsrStateAfterInformerCacheRead(request, response)
}

func (l *UnobsrStateListener) NotifyUnobsrStateAfterSideEffects(request *sieve.NotifyUnobsrStateAfterSideEffectsRequest, response *sieve.Response) error {
	return l.Server.NotifyUnobsrStateAfterSideEffects(request, response)
}

type unobsrStateServer struct {
	eventID          int32
	pausingReconcile bool
	diffCurEvent     map[string]interface{}
	diffPrevEvent    map[string]interface{}
	ceEtype          string
	ceName           string
	ceNamespace      string
	ceRtype          string
	reconcilingMutex *sync.RWMutex
	prevEvent        map[string]interface{}
	curEvent         map[string]interface{}
	eventCounter     int
	maskedKeysSet    map[string]struct{}
	maskedPathsSet   map[string]struct{}
}

func (s *unobsrStateServer) Start() {
	log.Println("start unobsrStateServer...")
	log.Printf("target event type: %s\n", s.ceEtype)
	log.Printf("target delta: prev: %s\n", mapToStr(s.diffPrevEvent))
	log.Printf("target delta: cur: %s\n", mapToStr(s.diffCurEvent))
}

// For now, we get an cruial event from API server, we want to see if any later event cancel this one
func (s *unobsrStateServer) NotifyUnobsrStateBeforeIndexerWrite(request *sieve.NotifyUnobsrStateBeforeIndexerWriteRequest, response *sieve.Response) error {
	currentEvent := strToMap(request.Object)
	if !(request.ResourceType == s.ceRtype && isSameObjectServerSide(currentEvent, s.ceNamespace, s.ceName)) {
		log.Fatalf("encounter unexpected object: %s %s", request.ResourceType, request.Object)
	}
	log.Println("NotifyUnobsrStateBeforeIndexerWrite", request.OperationType, request.ResourceType, request.Object)
	s.prevEvent = s.curEvent
	s.curEvent = currentEvent
	if findTargetDiff(s.eventCounter, request.OperationType, s.ceEtype, s.prevEvent, s.curEvent, s.diffPrevEvent, s.diffCurEvent, s.maskedKeysSet, s.maskedPathsSet, false) {
		startUnobsrStateInjection()
		log.Println("[sieve] should stop any reconcile here until a later cancel event comes")
		s.reconcilingMutex.Lock()
		s.pausingReconcile = true
		log.Println("[sieve] start to pause")
	}
	*response = sieve.Response{Message: request.OperationType, Ok: true}
	return nil
}

func (s *unobsrStateServer) NotifyUnobsrStateAfterIndexerWrite(request *sieve.NotifyUnobsrStateAfterIndexerWriteRequest, response *sieve.Response) error {
	currentEvent := strToMap(request.Object)
	if !(request.ResourceType == s.ceRtype && isSameObjectServerSide(currentEvent, s.ceNamespace, s.ceName)) {
		log.Fatalf("encounter unexpected object: %s %s", request.ResourceType, request.Object)
	}
	// If we are inside pausing, then we check for target event which can cancel the crucial one
	log.Println("NotifyUnobsrStateAfterIndexerWrite", s.pausingReconcile)
	if s.pausingReconcile {
		if conflictingEvent(s.ceEtype, request.OperationType, s.diffCurEvent, currentEvent, s.maskedKeysSet, s.maskedPathsSet) {
			// TODO: we should also consider the corner case where s.diffCurEvent == {}
			log.Printf("[sieve] we met the cancel event %s, reconcile is resumed\n", request.OperationType)
			log.Println("NotifyUnobsrStateAfterIndexerWrite", request.OperationType, request.ResourceType, request.Object)
			s.pausingReconcile = false
			s.reconcilingMutex.Unlock()
			finishUnobsrStateInjection()
		}
	}
	*response = sieve.Response{Ok: true}
	return nil
}

// Note that we are blocking the reconciler before reading the resource involved in the crucial event
// If the reconciler has already read some other resource in one reconcile,
// after removing the block there could be some inconsistency between the previously read data and the crucial event
func (s *unobsrStateServer) NotifyUnobsrStateBeforeInformerCacheRead(request *sieve.NotifyUnobsrStateBeforeInformerCacheReadRequest, response *sieve.Response) error {
	if request.OperationType == "Get" {
		if !(request.ResourceType == s.ceRtype && request.Name == s.ceName && request.Namespace == s.ceNamespace) {
			log.Fatalf("encounter unexpected object: %s %s %s", request.ResourceType, request.Namespace, request.Name)
		}
	} else {
		if !(request.ResourceType == s.ceRtype+"list") {
			log.Fatalf("encounter unexpected object: %s", request.ResourceType)
		}
	}
	log.Println("NotifyUnobsrStateBeforeInformerCacheRead[0/1]", s.pausingReconcile)
	s.reconcilingMutex.Lock()
	log.Println("NotifyUnobsrStateBeforeInformerCacheRead[1/1]", s.pausingReconcile)
	*response = sieve.Response{Ok: true}
	return nil
}

func (s *unobsrStateServer) NotifyUnobsrStateAfterInformerCacheRead(request *sieve.NotifyUnobsrStateAfterInformerCacheReadRequest, response *sieve.Response) error {
	if request.OperationType == "Get" {
		if !(request.ResourceType == s.ceRtype && request.Name == s.ceName && request.Namespace == s.ceNamespace) {
			log.Fatalf("encounter unexpected object: %s %s %s", request.ResourceType, request.Namespace, request.Name)
		}
	} else {
		if !(request.ResourceType == s.ceRtype+"list") {
			log.Fatalf("encounter unexpected object: %s", request.ResourceType)
		}
	}
	log.Println("NotifyUnobsrStateAfterInformerCacheRead")
	s.reconcilingMutex.Unlock()
	*response = sieve.Response{Ok: true}
	return nil
}

func (s *unobsrStateServer) NotifyUnobsrStateAfterSideEffects(request *sieve.NotifyUnobsrStateAfterSideEffectsRequest, response *sieve.Response) error {
	log.Printf("[SIEVE-AFTER-WRITE]\t%d\t%s\t%s\t%s\t%s\n", request.SideEffectID, request.SideEffectType, request.ResourceType, request.Error, request.Object)
	*response = sieve.Response{Message: request.SideEffectType, Ok: true}
	return nil
}
