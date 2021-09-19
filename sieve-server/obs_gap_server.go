package main

import (
	"log"
	"sync"
	"sync/atomic"
	"time"

	sieve "sieve.client"
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
	seenPrev           bool
	eventID            int32
	paused             bool
	pausingReconcile   bool
	crucialCur         string
	crucialPrev        string
	ceName             string
	ceNamespace        string
	ceRtype            string
	mutex              *sync.RWMutex
	reconcilingMutex   *sync.RWMutex
	cond               *sync.Cond
	pausedReconcileCnt int32
}

func (s *obsGapServer) Start() {
	log.Println("start obsGapServer...")
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

// For now, we get an cruial event from API server, we want to see if any later event cancel this one
func (s *obsGapServer) NotifyObsGapBeforeIndexerWrite(request *sieve.NotifyObsGapBeforeIndexerWriteRequest, response *sieve.Response) error {
	eID := atomic.AddInt32(&s.eventID, 1)
	log.Println("NotifyObsGapBeforeIndexerWrite", eID, request.OperationType, request.ResourceType, request.Object)
	currentEvent := strToMap(request.Object)
	crucialCurEvent := strToMap(s.crucialCur)
	crucialPrevEvent := strToMap(s.crucialPrev)
	// We then check for the crucial event
	if request.ResourceType == s.ceRtype && isSameObject(currentEvent, s.ceNamespace, s.ceName) && s.shouldPauseReconcile(crucialCurEvent, crucialPrevEvent, currentEvent) {
		s.reconcilingMutex.Lock()
		log.Println("[sieve] should stop any reconcile here until a later cancel event comes")
		s.mutex.Lock()
		s.pausingReconcile = true
		s.mutex.Unlock()
		s.reconcilingMutex.Unlock()

		go func() {
			time.Sleep(time.Second * 30)
			s.mutex.Lock()
			if s.pausingReconcile {
				s.pausingReconcile = false
				s.cond.Broadcast()
				log.Println("[sieve] we met the timeout for reconcile pausing, reconcile is resumed", s.pausedReconcileCnt)
			}
			s.mutex.Unlock()
		}()
	}
	*response = sieve.Response{Message: request.OperationType, Ok: true, Number: int(eID)}
	return nil
}

func (s *obsGapServer) NotifyObsGapAfterIndexerWrite(request *sieve.NotifyObsGapAfterIndexerWriteRequest, response *sieve.Response) error {
	// If we are inside pausing, then we check for target event which can cancel the crucial one
	pausingReconcile := false
	s.mutex.RLock()
	pausingReconcile = s.pausingReconcile
	s.mutex.RUnlock()

	log.Println("NotifyObsGapAfterIndexerWrite", pausingReconcile, "pausedReconcileCnt", s.pausedReconcileCnt)

	if pausingReconcile {
		currentEvent := strToMap(request.Object)
		crucialEvent := strToMap(s.crucialCur)
		if request.OperationType == "Deleted" && request.ResourceType == s.ceRtype && isSameObject(currentEvent, s.ceNamespace, s.ceName) {
			// Then we can resume all the reconcile
			log.Printf("[sieve] we met the later cancel event %s, reconcile is resumed, paused cnt: %d\n", request.OperationType, s.pausedReconcileCnt)
			log.Println("NotifyObsGapAfterIndexerWrite", request.OperationType, request.ResourceType, request.Object)
			s.mutex.Lock()
			s.pausingReconcile = false
			s.cond.Broadcast()
			s.mutex.Unlock()
		} else if request.ResourceType == s.ceRtype && isSameObject(currentEvent, s.ceNamespace, s.ceName) {
			// We also propose a diff based method for the cancel
			if cancelEvent(crucialEvent, currentEvent) {
				log.Printf("[sieve] we met the later cancel event %s, reconcile is resumed, paused cnt: %d\n", request.OperationType, s.pausedReconcileCnt)
				log.Println("NotifyObsGapAfterIndexerWrite", request.OperationType, request.ResourceType, request.Object)
				s.mutex.Lock()
				s.pausingReconcile = false
				s.cond.Broadcast()
				s.mutex.Unlock()
			}
		}

	}
	*response = sieve.Response{Ok: true}
	return nil
}

func (s *obsGapServer) NotifyObsGapBeforeReconcile(request *sieve.NotifyObsGapBeforeReconcileRequest, response *sieve.Response) error {
	s.reconcilingMutex.Lock()
	recID := request.ControllerName
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
	*response = sieve.Response{Ok: true}
	return nil
}

func (s *obsGapServer) NotifyObsGapAfterReconcile(request *sieve.NotifyObsGapAfterReconcileRequest, response *sieve.Response) error {
	recID := request.ControllerName
	log.Println("NotifyObsGapAfterReconcile", recID)
	*response = sieve.Response{Ok: true}
	s.reconcilingMutex.Unlock()
	return nil
}

func (s *obsGapServer) NotifyObsGapAfterSideEffects(request *sieve.NotifyObsGapAfterSideEffectsRequest, response *sieve.Response) error {
	log.Printf("[SIEVE-AFTER-SIDE-EFFECT]\t%d\t%s\t%s\t%s\t%s\n", request.SideEffectID, request.SideEffectType, request.ResourceType, request.Error, request.Object)
	*response = sieve.Response{Message: request.SideEffectType, Ok: true}
	return nil
}
