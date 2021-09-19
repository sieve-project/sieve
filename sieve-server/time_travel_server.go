package main

import (
	"log"
	"time"

	sieve "sieve.client"
)

// The listener is actually a wrapper around the server.
func NewTimeTravelListener(config map[interface{}]interface{}) *TimeTravelListener {
	server := &timeTravelServer{
		project:     config["project"].(string),
		seenPrev:    false,
		paused:      false,
		restarted:   false,
		pauseCh:     make(chan int),
		straggler:   config["straggler"].(string),
		crucialCur:  config["ce-diff-current"].(string),
		crucialPrev: config["ce-diff-previous"].(string),
		podLabel:    config["operator-pod-label"].(string),
		frontRunner: config["front-runner"].(string),
		deployName:  config["deployment-name"].(string),
		namespace:   "default",
	}
	listener := &TimeTravelListener{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

type TimeTravelListener struct {
	Server *timeTravelServer
}

// Echo is just for testing.
func (l *TimeTravelListener) Echo(request *sieve.EchoRequest, response *sieve.Response) error {
	*response = sieve.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *TimeTravelListener) NotifyTimeTravelCrucialEvent(request *sieve.NotifyTimeTravelCrucialEventRequest, response *sieve.Response) error {
	return l.Server.NotifyTimeTravelCrucialEvent(request, response)
}

func (l *TimeTravelListener) NotifyTimeTravelRestartPoint(request *sieve.NotifyTimeTravelRestartPointRequest, response *sieve.Response) error {
	return l.Server.NotifyTimeTravelRestartPoint(request, response)
}

func (l *TimeTravelListener) NotifyTimeTravelAfterSideEffects(request *sieve.NotifyTimeTravelAfterSideEffectsRequest, response *sieve.Response) error {
	return l.Server.NotifyTimeTravelAfterSideEffects(request, response)
}

type timeTravelServer struct {
	project     string
	straggler   string
	frontRunner string
	crucialCur  string
	crucialPrev string
	podLabel    string
	seenPrev    bool
	paused      bool
	restarted   bool
	pauseCh     chan int
	deployName  string
	namespace   string
}

func (s *timeTravelServer) Start() {
	log.Println("start timeTravelServer...")
}

func (s *timeTravelServer) NotifyTimeTravelCrucialEvent(request *sieve.NotifyTimeTravelCrucialEventRequest, response *sieve.Response) error {
	log.Printf("NotifyTimeTravelCrucialEvent: Hostname: %s\n", request.Hostname)
	if s.straggler != request.Hostname {
		*response = sieve.Response{Message: request.Hostname, Ok: true}
		return nil
	}
	currentEvent := strToMap(request.Object)
	crucialCurEvent := strToMap(s.crucialCur)
	crucialPrevEvent := strToMap(s.crucialPrev)
	log.Printf("[sieve][current-event] %s\n", request.Object)
	if s.shouldPause(crucialCurEvent, crucialPrevEvent, currentEvent) {
		log.Println("[sieve] should sleep here")
		<-s.pauseCh
		log.Println("[sieve] sleep over")
	}
	*response = sieve.Response{Message: request.Hostname, Ok: true}
	return nil
}

func (s *timeTravelServer) NotifyTimeTravelRestartPoint(request *sieve.NotifyTimeTravelRestartPointRequest, response *sieve.Response) error {
	log.Printf("NotifyTimeTravelSideEffect: Hostname: %s\n", request.Hostname)
	if s.frontRunner != request.Hostname {
		*response = sieve.Response{Message: request.Hostname, Ok: true}
		return nil
	}
	log.Printf("[sieve][restart-point] %s %s %s %s\n", request.Name, request.Namespace, request.ResourceType, request.EventType)
	if s.shouldRestart() {
		log.Println("[sieve] should restart here")
		go s.waitAndRestartComponent()
	}
	*response = sieve.Response{Message: request.Hostname, Ok: true}
	return nil
}

func (s *timeTravelServer) NotifyTimeTravelAfterSideEffects(request *sieve.NotifyTimeTravelAfterSideEffectsRequest, response *sieve.Response) error {
	log.Printf("[SIEVE-AFTER-SIDE-EFFECT]\t%d\t%s\t%s\t%s\t%s\n", request.SideEffectID, request.SideEffectType, request.ResourceType, request.Error, request.Object)
	*response = sieve.Response{Message: request.SideEffectType, Ok: true}
	return nil
}

func (s *timeTravelServer) waitAndRestartComponent() {
	time.Sleep(time.Duration(10) * time.Second)
	restartOperator(s.namespace, s.deployName, s.podLabel, s.frontRunner, s.straggler, true)
	time.Sleep(time.Duration(20) * time.Second)
	s.pauseCh <- 0
}

func (s *timeTravelServer) shouldPause(crucialCurEvent, crucialPrevEvent, currentEvent map[string]interface{}) bool {
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
			// else if s.isCrucial(crucialPrevEvent, currentEvent) {
			// 	log.Println("Meet crucialPrevEvent: keep seenPrev as true")
			// 	// s.seenPrev = true
			// } else {
			// 	log.Println("Not meet anything: set seenPrev back to false")
			// 	s.seenPrev = false
			// }
		}
	}
	return false
}

func (s *timeTravelServer) shouldRestart() bool {
	if s.paused && !s.restarted {
		s.restarted = true
		return true
	} else {
		return false
	}
}
