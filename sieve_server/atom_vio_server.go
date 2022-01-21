package main

import (
	"log"
	"sync"

	sieve "sieve.client"
)

func NewIntmdStateListener(config map[interface{}]interface{}, learnedMask map[string]map[string][]string, configuredMask map[string][]string) *IntmdStateListener {
	maskedKeysSet, maskedPathsSet := mergeAndRefineMask(config["se-rtype"].(string), config["se-name"].(string), learnedMask, configuredMask)
	server := &intmdStateServer{
		restarted:              false,
		eventID:                -1,
		frontRunner:            config["front-runner"].(string),
		deployName:             config["deployment-name"].(string),
		namespace:              "default",
		podLabel:               config["operator-pod-label"].(string),
		seName:                 config["se-name"].(string),
		seNamespace:            config["se-namespace"].(string),
		seRtype:                config["se-rtype"].(string),
		seEtypePrev:            config["se-etype-previous"].(string),
		seEtype:                config["se-etype-current"].(string),
		diffPrevEvent:          strToMap(config["se-diff-previous"].(string)),
		diffCurEvent:           strToMap(config["se-diff-current"].(string)),
		eventCounter:           strToInt(config["se-counter"].(string)),
		prevEventPerReconciler: make(map[string]map[string]interface{}),
		curEventPerReconciler:  make(map[string]map[string]interface{}),
		maskedKeysSet:          maskedKeysSet,
		maskedPathsSet:         maskedPathsSet,
		reconcilingMutex:       &sync.RWMutex{},
	}
	listener := &IntmdStateListener{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

type IntmdStateListener struct {
	Server *intmdStateServer
}

func (l *IntmdStateListener) Echo(request *sieve.EchoRequest, response *sieve.Response) error {
	*response = sieve.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *IntmdStateListener) NotifyIntmdStateAfterOperatorGet(request *sieve.NotifyIntmdStateAfterOperatorGetRequest, response *sieve.Response) error {
	return l.Server.NotifyIntmdStateAfterOperatorGet(request, response)
}

func (l *IntmdStateListener) NotifyIntmdStateAfterOperatorList(request *sieve.NotifyIntmdStateAfterOperatorListRequest, response *sieve.Response) error {
	return l.Server.NotifyIntmdStateAfterOperatorList(request, response)
}

func (l *IntmdStateListener) NotifyIntmdStateAfterSideEffects(request *sieve.NotifyIntmdStateAfterSideEffectsRequest, response *sieve.Response) error {
	return l.Server.NotifyIntmdStateAfterSideEffects(request, response)
}

type intmdStateServer struct {
	restarted              bool
	frontRunner            string
	deployName             string
	namespace              string
	podLabel               string
	eventID                int32
	seName                 string
	seNamespace            string
	seRtype                string
	seEtype                string
	diffCurEvent           map[string]interface{}
	diffPrevEvent          map[string]interface{}
	seEtypePrev            string
	prevEventPerReconciler map[string]map[string]interface{}
	curEventPerReconciler  map[string]map[string]interface{}
	eventCounter           int
	maskedKeysSet          map[string]struct{}
	maskedPathsSet         map[string]struct{}
	reconcilingMutex       *sync.RWMutex
}

func (s *intmdStateServer) Start() {
	log.Println("start intmdStateServer...")
	log.Printf("target event type: %s\n", s.seEtype)
	log.Printf("target delta: prev: %s\n", mapToStr(s.diffPrevEvent))
	log.Printf("target delta: cur: %s\n", mapToStr(s.diffCurEvent))
}

func (s *intmdStateServer) NotifyIntmdStateAfterOperatorGet(request *sieve.NotifyIntmdStateAfterOperatorGetRequest, response *sieve.Response) error {
	s.reconcilingMutex.Lock()
	defer s.reconcilingMutex.Unlock()
	readObj := strToMap(request.Object)
	if !(request.ResourceType == s.seRtype && s.seEtypePrev == "Get" && isSameObjectServerSide(readObj, s.seNamespace, s.seName)) {
		log.Fatalf("encounter unexpected Get: %s %s %s", request.ResourceType, request.Error, request.Object)
	}
	log.Printf("[SIEVE-AFTER-READ]\tGet\t%s\t%s\t%s\t%s\t%s", request.ResourceType, request.Namespace, request.Name, request.Error, request.Object)
	s.prevEventPerReconciler[request.ReconcilerType] = readObj
	trimKindApiversion(s.prevEventPerReconciler[request.ReconcilerType])
	*response = sieve.Response{Message: request.ResourceType, Ok: true}
	return nil
}

func (s *intmdStateServer) NotifyIntmdStateAfterOperatorList(request *sieve.NotifyIntmdStateAfterOperatorListRequest, response *sieve.Response) error {
	s.reconcilingMutex.Lock()
	defer s.reconcilingMutex.Unlock()
	if !(request.ResourceType == s.seRtype+"list" && s.seEtypePrev == "List") {
		log.Fatalf("encounter unexpected List: %s %s %s", request.ResourceType, request.Error, request.ObjectList)
	}
	log.Printf("[SIEVE-AFTER-READ]\tList\t%s\t%s\t%s", request.ResourceType, request.Error, request.ObjectList)
	readObjs := strToMap(request.ObjectList)["items"].([]interface{})
	for _, readObj := range readObjs {
		if isSameObjectServerSide(readObj.(map[string]interface{}), s.seNamespace, s.seName) {
			s.prevEventPerReconciler[request.ReconcilerType] = readObj.(map[string]interface{})
			trimKindApiversion(s.prevEventPerReconciler[request.ReconcilerType])
			break
		}
	}
	*response = sieve.Response{Message: request.ResourceType, Ok: true}
	return nil
}

func (s *intmdStateServer) NotifyIntmdStateAfterSideEffects(request *sieve.NotifyIntmdStateAfterSideEffectsRequest, response *sieve.Response) error {
	s.reconcilingMutex.Lock()
	defer s.reconcilingMutex.Unlock()
	writeObj := strToMap(request.Object)
	if !(request.ResourceType == s.seRtype && isSameObjectServerSide(writeObj, s.seNamespace, s.seName) && request.Error == "NoError") {
		log.Fatalf("encounter unexpected Write: %s %s %s %s", request.SideEffectType, request.ResourceType, request.Error, request.Object)
	}
	log.Printf("[SIEVE-AFTER-WRITE]\t%d\t%s\t%s\t%s\t%s\n", request.SideEffectID, request.SideEffectType, request.ResourceType, request.Error, request.Object)
	s.curEventPerReconciler[request.ReconcilerType] = writeObj
	trimKindApiversion(s.curEventPerReconciler[request.ReconcilerType])
	if _, ok := s.prevEventPerReconciler[request.ReconcilerType]; !ok {
		s.prevEventPerReconciler[request.ReconcilerType] = make(map[string]interface{})
	}
	log.Printf("reconciler name: %s\n", request.ReconcilerType)
	log.Printf("number of reconcilers: %d\n", len(s.prevEventPerReconciler))
	if findTargetDiff(s.eventCounter, request.SideEffectType, s.seEtype, s.prevEventPerReconciler[request.ReconcilerType], s.curEventPerReconciler[request.ReconcilerType], s.diffPrevEvent, s.diffCurEvent, s.maskedKeysSet, s.maskedPathsSet, false) {
		log.Println("ready to crash!")
		startIntmdStateInjection()
		restartOperator(s.namespace, s.deployName, s.podLabel, s.frontRunner, "", false)
		finishIntmdStateInjection()
	}
	*response = sieve.Response{Message: request.SideEffectType, Ok: true}
	return nil
}
