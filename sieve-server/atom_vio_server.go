package main

import (
	"log"

	sieve "sieve.client"
)

func NewAtomVioListener(config map[interface{}]interface{}) *AtomVioListener {
	server := &atomVioServer{
		restarted:     false,
		eventID:       -1,
		frontRunner:   config["front-runner"].(string),
		deployName:    config["deployment-name"].(string),
		namespace:     "default",
		podLabel:      config["operator-pod-label"].(string),
		seName:        config["se-name"].(string),
		seNamespace:   config["se-namespace"].(string),
		seRtype:       config["se-rtype"].(string),
		seEtypePrev:   config["se-etype-previous"].(string),
		seEtype:       config["se-etype-current"].(string),
		diffPrevEvent: strToMap(config["se-diff-previous"].(string)),
		diffCurEvent:  strToMap(config["se-diff-current"].(string)),
		eventCounter:  strToInt(config["se-counter"].(string)),
		prevEvent:     nil,
		curEvent:      nil,
	}
	listener := &AtomVioListener{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

type AtomVioListener struct {
	Server *atomVioServer
}

func (l *AtomVioListener) Echo(request *sieve.EchoRequest, response *sieve.Response) error {
	*response = sieve.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *AtomVioListener) NotifyAtomVioAfterOperatorGet(request *sieve.NotifyAtomVioAfterOperatorGetRequest, response *sieve.Response) error {
	return l.Server.NotifyAtomVioAfterOperatorGet(request, response)
}

func (l *AtomVioListener) NotifyAtomVioAfterOperatorList(request *sieve.NotifyAtomVioAfterOperatorListRequest, response *sieve.Response) error {
	return l.Server.NotifyAtomVioAfterOperatorList(request, response)
}

func (l *AtomVioListener) NotifyAtomVioAfterSideEffects(request *sieve.NotifyAtomVioAfterSideEffectsRequest, response *sieve.Response) error {
	return l.Server.NotifyAtomVioAfterSideEffects(request, response)
}

type atomVioServer struct {
	restarted     bool
	frontRunner   string
	deployName    string
	namespace     string
	podLabel      string
	eventID       int32
	seName        string
	seNamespace   string
	seRtype       string
	seEtype       string
	diffCurEvent  map[string]interface{}
	diffPrevEvent map[string]interface{}
	seEtypePrev   string
	prevEvent     map[string]interface{}
	curEvent      map[string]interface{}
	eventCounter  int
}

func (s *atomVioServer) Start() {
	log.Println("start atomVioServer...")
	log.Printf("target event type: %s\n", s.seEtype)
	log.Printf("target delta: prev: %s\n", mapToStr(s.diffPrevEvent))
	log.Printf("target delta: cur: %s\n", mapToStr(s.diffCurEvent))
}

func (s *atomVioServer) NotifyAtomVioAfterOperatorGet(request *sieve.NotifyAtomVioAfterOperatorGetRequest, response *sieve.Response) error {
	readObj := strToMap(request.Object)
	if !(request.ResourceType == s.seRtype && s.seEtypePrev == "Get" && isSameObjectServerSide(readObj, s.seNamespace, s.seName)) {
		log.Fatalf("encounter unexpected Get: %s %s %s", request.ResourceType, request.Error, request.Object)
	}
	log.Printf("[SIEVE-AFTER-READ]\tGet\t%s\t%s\t%s\t%s\t%s", request.ResourceType, request.Namespace, request.Name, request.Error, request.Object)
	s.prevEvent = readObj
	trimKindApiversion(s.prevEvent)
	*response = sieve.Response{Message: request.ResourceType, Ok: true}
	return nil
}

func (s *atomVioServer) NotifyAtomVioAfterOperatorList(request *sieve.NotifyAtomVioAfterOperatorListRequest, response *sieve.Response) error {
	if !(request.ResourceType == s.seRtype+"list" && s.seEtypePrev == "List") {
		log.Fatalf("encounter unexpected List: %s %s %s", request.ResourceType, request.Error, request.ObjectList)
	}
	log.Printf("[SIEVE-AFTER-READ]\tList\t%s\t%s\t%s", request.ResourceType, request.Error, request.ObjectList)
	readObjs := strToMap(request.ObjectList)["items"].([]interface{})
	for _, readObj := range readObjs {
		if isSameObjectServerSide(readObj.(map[string]interface{}), s.seNamespace, s.seName) {
			s.prevEvent = readObj.(map[string]interface{})
			trimKindApiversion(s.prevEvent)
			break
		}
	}
	*response = sieve.Response{Message: request.ResourceType, Ok: true}
	return nil
}

func (s *atomVioServer) NotifyAtomVioAfterSideEffects(request *sieve.NotifyAtomVioAfterSideEffectsRequest, response *sieve.Response) error {
	writeObj := strToMap(request.Object)
	if !(request.ResourceType == s.seRtype && isSameObjectServerSide(writeObj, s.seNamespace, s.seName) && request.Error == "NoError") {
		log.Fatalf("encounter unexpected Write: %s %s %s %s", request.SideEffectType, request.ResourceType, request.Error, request.Object)
	}
	log.Printf("[SIEVE-AFTER-WRITE]\t%d\t%s\t%s\t%s\t%s\n", request.SideEffectID, request.SideEffectType, request.ResourceType, request.Error, request.Object)
	s.curEvent = writeObj
	trimKindApiversion(s.curEvent)
	if findTargetDiff(s.eventCounter, request.SideEffectType, s.seEtype, s.prevEvent, s.curEvent, s.diffPrevEvent, s.diffCurEvent, false) {
		log.Println("ready to crash!")
		startAtomVioInjection()
		restartOperator(s.namespace, s.deployName, s.podLabel, s.frontRunner, "", false)
		finishAtomVioInjection()
	}
	*response = sieve.Response{Message: request.SideEffectType, Ok: true}
	return nil
}
