package main

import (
	"log"
	"time"

	sieve "sieve.client"
)

// The listener is actually a wrapper around the server.
func NewStaleStateListener(config map[interface{}]interface{}, learnedFieldPathMask, configuredFieldPathMask, configuredFieldKeyMask map[string][]string) *StaleStateListener {
	maskedKeysSet, maskedPathsSet := mergeAndRefineMask(config["ce-rtype"].(string), config["ce-namespace"].(string), config["ce-name"].(string), learnedFieldPathMask, configuredFieldPathMask, configuredFieldKeyMask)
	server := &staleStateServer{
		project:        config["project"].(string),
		restarted:      false,
		pauseCh:        make(chan int),
		straggler:      config["straggler"].(string),
		ceEtype:        config["ce-etype-current"].(string),
		ceIsCR:         strToBool(config["ce-is-cr"].(string)),
		diffCurEvent:   strToMap(config["ce-diff-current"].(string)),
		diffPrevEvent:  strToMap(config["ce-diff-previous"].(string)),
		eventCounter:   strToInt(config["ce-counter"].(string)),
		podLabel:       config["operator-pod-label"].(string),
		frontRunner:    config["front-runner"].(string),
		deployName:     config["deployment-name"].(string),
		namespace:      "default",
		prevEvent:      make(map[string]interface{}),
		curEvent:       make(map[string]interface{}),
		sleeped:        false,
		maskedKeysSet:  maskedKeysSet,
		maskedPathsSet: maskedPathsSet,
	}
	listener := &StaleStateListener{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

type StaleStateListener struct {
	Server *staleStateServer
}

// Echo is just for testing.
func (l *StaleStateListener) Echo(request *sieve.EchoRequest, response *sieve.Response) error {
	*response = sieve.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *StaleStateListener) NotifyStaleStateCrucialEvent(request *sieve.NotifyStaleStateCrucialEventRequest, response *sieve.Response) error {
	return l.Server.NotifyStaleStateCrucialEvent(request, response)
}

func (l *StaleStateListener) NotifyStaleStateRestartPoint(request *sieve.NotifyStaleStateRestartPointRequest, response *sieve.Response) error {
	return l.Server.NotifyStaleStateRestartPoint(request, response)
}

func (l *StaleStateListener) NotifyStaleStateAfterSideEffects(request *sieve.NotifyStaleStateAfterSideEffectsRequest, response *sieve.Response) error {
	return l.Server.NotifyStaleStateAfterSideEffects(request, response)
}

type staleStateServer struct {
	project        string
	straggler      string
	frontRunner    string
	ceEtype        string
	diffCurEvent   map[string]interface{}
	diffPrevEvent  map[string]interface{}
	podLabel       string
	restarted      bool
	pauseCh        chan int
	deployName     string
	namespace      string
	prevEvent      map[string]interface{}
	curEvent       map[string]interface{}
	sleeped        bool
	eventCounter   int
	ceIsCR         bool
	maskedKeysSet  map[string]struct{}
	maskedPathsSet map[string]struct{}
}

func (s *staleStateServer) Start() {
	if !s.ceIsCR {
		log.Printf("conforming diffCurEvent %v...\n", s.diffCurEvent)
		log.Printf("conforming diffPrevEvent %v...\n", s.diffPrevEvent)
		s.diffCurEvent = conformToAPIEvent(s.diffCurEvent)
		s.diffPrevEvent = conformToAPIEvent(s.diffPrevEvent)
		log.Printf("conform diffCurEvent to %v\n", s.diffCurEvent)
		log.Printf("conform diffPrevEvent to %v\n", s.diffPrevEvent)
		log.Printf("conforming maskedKeysSet %v...\n", s.maskedKeysSet)
		s.maskedKeysSet = conformToAPIKeys(s.maskedKeysSet)
		log.Printf("conform maskedKeysSet to %v\n", s.maskedKeysSet)
		log.Printf("conforming maskedPathsSet %v...\n", s.maskedPathsSet)
		s.maskedPathsSet = conformToAPIPaths(s.maskedPathsSet)
		log.Printf("conform maskedPathsSet to %v\n", s.maskedPathsSet)
	}
	log.Println("start staleStateServer...")
	log.Printf("target event type: %s\n", s.ceEtype)
	log.Printf("target delta: prev: %s\n", mapToStr(s.diffPrevEvent))
	log.Printf("target delta: cur: %s\n", mapToStr(s.diffCurEvent))
}

func (s *staleStateServer) NotifyStaleStateCrucialEvent(request *sieve.NotifyStaleStateCrucialEventRequest, response *sieve.Response) error {
	log.Printf("NotifyStaleStateCrucialEvent: Hostname: %s\n", request.Hostname)
	if s.straggler != request.Hostname {
		*response = sieve.Response{Message: request.Hostname, Ok: true}
		return nil
	}
	currentEvent := strToMap(request.Object)
	log.Printf("[sieve][current-event] %s\n", request.Object)
	s.prevEvent = s.curEvent
	s.curEvent = currentEvent
	if findTargetDiff(s.eventCounter, request.EventType, s.ceEtype, s.prevEvent, s.curEvent, s.diffPrevEvent, s.diffCurEvent, s.maskedKeysSet, s.maskedPathsSet, true) {
		s.sleeped = true
		startStaleStateInjection()
		log.Println("[sieve] should sleep here")
		<-s.pauseCh
		log.Println("[sieve] sleep over")
		finishStaleStateInjection()
	}
	*response = sieve.Response{Message: request.Hostname, Ok: true}
	return nil
}

func (s *staleStateServer) NotifyStaleStateRestartPoint(request *sieve.NotifyStaleStateRestartPointRequest, response *sieve.Response) error {
	log.Printf("NotifyStaleStateSideEffect: Hostname: %s\n", request.Hostname)
	if s.frontRunner != request.Hostname {
		*response = sieve.Response{Message: request.Hostname, Ok: true}
		return nil
	}
	log.Printf("[sieve][restart-point] %s %s %s %s\n", request.Name, request.Namespace, request.ResourceType, request.EventType)
	if s.shouldRestart() {
		log.Println("[sieve] should restart here")
		go s.waitAndRestartOperator()
	}
	*response = sieve.Response{Message: request.Hostname, Ok: true}
	return nil
}

func (s *staleStateServer) NotifyStaleStateAfterSideEffects(request *sieve.NotifyStaleStateAfterSideEffectsRequest, response *sieve.Response) error {
	log.Printf("[SIEVE-AFTER-WRITE]\t%d\t%s\t%s\t%s\t%s\n", request.SideEffectID, request.SideEffectType, request.ResourceType, request.Error, request.Object)
	*response = sieve.Response{Message: request.SideEffectType, Ok: true}
	return nil
}

func (s *staleStateServer) waitAndRestartOperator() {
	time.Sleep(time.Duration(10) * time.Second)
	restartOperator(s.namespace, s.deployName, s.podLabel, s.frontRunner, s.straggler, true)
	time.Sleep(time.Duration(20) * time.Second)
	s.pauseCh <- 0
}

func (s *staleStateServer) shouldRestart() bool {
	if s.sleeped && !s.restarted {
		s.restarted = true
		return true
	} else {
		return false
	}
}
