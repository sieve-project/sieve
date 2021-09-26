package main

import (
	"log"
	"sync"
	"sync/atomic"

	sieve "sieve.client"
)

func NewObsGapListener(config map[interface{}]interface{}) *ObsGapListener {
	server := &obsGapServer{
		eventID:            -1,
		pausingReconcile:   false,
		diffCurEvent:       strToMap(config["ce-diff-current"].(string)),
		diffPrevEvent:      strToMap(config["ce-diff-previous"].(string)),
		ceName:             config["ce-name"].(string),
		ceNamespace:        config["ce-namespace"].(string),
		ceRtype:            config["ce-rtype"].(string),
		pausedReconcileCnt: 0,
		prevEvent:          nil,
		curEvent:           nil,
	}
	server.mutex = &sync.RWMutex{}
	// TODO: the reconcilingMutex might affect the performace of concurrent reconcile
	// we can live with it for now as operators usually do not run reconcile concurrently
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

func (l *ObsGapListener) NotifyObsGapBeforeReconcile(request *sieve.NotifyObsGapBeforeReconcileRequest, response *sieve.Response) error {
	return l.Server.NotifyObsGapBeforeReconcile(request, response)
}

func (l *ObsGapListener) NotifyObsGapAfterReconcile(request *sieve.NotifyObsGapAfterReconcileRequest, response *sieve.Response) error {
	return l.Server.NotifyObsGapAfterReconcile(request, response)
}

func (l *ObsGapListener) NotifyObsGapAfterSideEffects(request *sieve.NotifyObsGapAfterSideEffectsRequest, response *sieve.Response) error {
	return l.Server.NotifyObsGapAfterSideEffects(request, response)
}

type obsGapServer struct {
	eventID            int32
	pausingReconcile   bool
	diffCurEvent       map[string]interface{}
	diffPrevEvent      map[string]interface{}
	ceName             string
	ceNamespace        string
	ceRtype            string
	mutex              *sync.RWMutex
	reconcilingMutex   *sync.RWMutex
	cond               *sync.Cond
	pausedReconcileCnt int32
	prevEvent          map[string]interface{}
	curEvent           map[string]interface{}
}

func (s *obsGapServer) Start() {
	log.Println("start obsGapServer...")
	log.Printf("target delta: prev: %s\n", mapToStr(s.diffPrevEvent))
	log.Printf("target delta: cur: %s\n", mapToStr(s.diffCurEvent))
}

// For now, we get an cruial event from API server, we want to see if any later event cancel this one
func (s *obsGapServer) NotifyObsGapBeforeIndexerWrite(request *sieve.NotifyObsGapBeforeIndexerWriteRequest, response *sieve.Response) error {
	log.Println("NotifyObsGapBeforeIndexerWrite", request.OperationType, request.ResourceType, request.Object)
	currentEvent := strToMap(request.Object)
	if !(request.ResourceType == s.ceRtype && isSameObjectServerSide(currentEvent, s.ceNamespace, s.ceName)) {
		log.Fatalf("encounter unexpected object: %s %s", request.ResourceType, request.Object)
	}
	s.prevEvent = s.curEvent
	s.curEvent = currentEvent
	if findTargetDiff(s.prevEvent, s.curEvent, s.diffPrevEvent, s.diffCurEvent, false) {
		startObsGapInjection()
		log.Println("[sieve] should stop any reconcile here until a later cancel event comes")
		s.reconcilingMutex.Lock()
		s.mutex.Lock()
		s.pausingReconcile = true
		s.mutex.Unlock()
		s.reconcilingMutex.Unlock()
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
	s.mutex.RLock()
	pausingReconcile := s.pausingReconcile
	s.mutex.RUnlock()

	log.Println("NotifyObsGapAfterIndexerWrite", pausingReconcile, "pausedReconcileCnt", s.pausedReconcileCnt)

	if pausingReconcile {
		if request.OperationType == "Deleted" {
			log.Printf("[sieve] we met the later cancel event %s, reconcile is resumed, paused cnt: %d\n", request.OperationType, s.pausedReconcileCnt)
			log.Println("NotifyObsGapAfterIndexerWrite", request.OperationType, request.ResourceType, request.Object)
			s.mutex.Lock()
			s.pausingReconcile = false
			s.cond.Broadcast()
			s.mutex.Unlock()
			finishObsGapInjection()
		} else {
			// TODO: we should also consider the corner case where s.diffCurEvent == {}
			if conflictingEventAsMap(s.diffCurEvent, currentEvent) {
				log.Printf("[sieve] we met the later cancel event %s, reconcile is resumed, paused cnt: %d\n", request.OperationType, s.pausedReconcileCnt)
				log.Println("NotifyObsGapAfterIndexerWrite", request.OperationType, request.ResourceType, request.Object)
				s.mutex.Lock()
				s.pausingReconcile = false
				s.cond.Broadcast()
				s.mutex.Unlock()
				finishObsGapInjection()
			}
		}

	}
	*response = sieve.Response{Ok: true}
	return nil
}

func (s *obsGapServer) NotifyObsGapBeforeReconcile(request *sieve.NotifyObsGapBeforeReconcileRequest, response *sieve.Response) error {
	s.reconcilingMutex.Lock()
	recID := request.ControllerName
	s.mutex.Lock()
	log.Println("NotifyObsGapBeforeReconcile[0/1]", recID, s.pausingReconcile)
	if s.pausingReconcile {
		atomic.AddInt32(&s.pausedReconcileCnt, 1)
	}
	for s.pausingReconcile {
		s.cond.Wait()
	}
	log.Println("NotifyObsGapBeforeReconcile[1/1]", recID, s.pausingReconcile)
	s.mutex.Unlock()
	*response = sieve.Response{Ok: true}
	return nil
}

func (s *obsGapServer) NotifyObsGapAfterReconcile(request *sieve.NotifyObsGapAfterReconcileRequest, response *sieve.Response) error {
	recID := request.ControllerName
	log.Println("NotifyObsGapAfterReconcile", recID)
	s.reconcilingMutex.Unlock()
	*response = sieve.Response{Ok: true}
	return nil
}

func (s *obsGapServer) NotifyObsGapAfterSideEffects(request *sieve.NotifyObsGapAfterSideEffectsRequest, response *sieve.Response) error {
	log.Printf("[SIEVE-AFTER-SIDE-EFFECT]\t%d\t%s\t%s\t%s\t%s\n", request.SideEffectID, request.SideEffectType, request.ResourceType, request.Error, request.Object)
	*response = sieve.Response{Message: request.SideEffectType, Ok: true}
	return nil
}
