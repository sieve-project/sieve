package main

import (
	"fmt"
	"log"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	sieve "sieve.client"
)

func NewLearnListener(config map[interface{}]interface{}) *LearnListener {
	rateLimiterEnabledFromConfig, err := strconv.ParseBool(config["rate-limiter-enabled"].(string))
	if err != nil {
		log.Fatal("invalid rate-limiter-enabled in config")
	}
	rateLimiterIntervalFromConfig, err := strconv.ParseInt(config["rate-limiter-interval"].(string), 10, 64)
	if err != nil {
		log.Fatal("invalid rate-limiter-interval in config")
	}
	server := &learnServer{
		rateLimitedEventCh:  make(chan notificationWrapper, 500),
		eventID:             -1,
		sideEffectID:        -1,
		eventChMap:          sync.Map{},
		sideEffectChMap:     sync.Map{},
		reconcileChMap:      sync.Map{},
		notificationCh:      make(chan notificationWrapper, 500),
		ongoingReconcileCnt: 0,
		reconcileCntMap:     map[string]int{},
		rateLimiterEnabled:  rateLimiterEnabledFromConfig,
		rateLimiterInterval: rateLimiterIntervalFromConfig,
	}
	listener := &LearnListener{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

type LearnListener struct {
	Server *learnServer
}

func (l *LearnListener) Echo(request *sieve.EchoRequest, response *sieve.Response) error {
	*response = sieve.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *LearnListener) NotifyLearnBeforeIndexerWrite(request *sieve.NotifyLearnBeforeIndexerWriteRequest, response *sieve.Response) error {
	return l.Server.NotifyLearnBeforeIndexerWrite(request, response)
}

func (l *LearnListener) NotifyLearnAfterIndexerWrite(request *sieve.NotifyLearnAfterIndexerWriteRequest, response *sieve.Response) error {
	return l.Server.NotifyLearnAfterIndexerWrite(request, response)
}

func (l *LearnListener) NotifyLearnBeforeReconcile(request *sieve.NotifyLearnBeforeReconcileRequest, response *sieve.Response) error {
	return l.Server.NotifyLearnBeforeReconcile(request, response)
}

func (l *LearnListener) NotifyLearnAfterReconcile(request *sieve.NotifyLearnAfterReconcileRequest, response *sieve.Response) error {
	return l.Server.NotifyLearnAfterReconcile(request, response)
}

func (l *LearnListener) NotifyLearnBeforeSideEffects(request *sieve.NotifyLearnBeforeSideEffectsRequest, response *sieve.Response) error {
	return l.Server.NotifyLearnBeforeSideEffects(request, response)
}

func (l *LearnListener) NotifyLearnAfterSideEffects(request *sieve.NotifyLearnAfterSideEffectsRequest, response *sieve.Response) error {
	return l.Server.NotifyLearnAfterSideEffects(request, response)
}

func (l *LearnListener) NotifyLearnAfterOperatorGet(request *sieve.NotifyLearnAfterOperatorGetRequest, response *sieve.Response) error {
	return l.Server.NotifyLearnAfterOperatorGet(request, response)
}

func (l *LearnListener) NotifyLearnAfterOperatorList(request *sieve.NotifyLearnAfterOperatorListRequest, response *sieve.Response) error {
	return l.Server.NotifyLearnAfterOperatorList(request, response)
}

type NotificationType int

const (
	beforeReconcile NotificationType = iota
	afterReconcile
	beforeSideEffect
	afterSideEffect
	afterRead
	beforeEvent
	afterEvent
)

type notificationWrapper struct {
	ntype   NotificationType
	payload string
}

type learnServer struct {
	rateLimitedEventCh  chan notificationWrapper
	eventID             int32
	sideEffectID        int32
	eventChMap          sync.Map
	sideEffectChMap     sync.Map
	reconcileChMap      sync.Map
	notificationCh      chan notificationWrapper
	ongoingReconcileCnt int
	reconcileCntMap     map[string]int
	rateLimiterEnabled  bool
	rateLimiterInterval int64
}

func (s *learnServer) Start() {
	log.Println("start learnServer...")
	go s.coordinatingEvents()
}

func (s *learnServer) NotifyLearnBeforeIndexerWrite(request *sieve.NotifyLearnBeforeIndexerWriteRequest, response *sieve.Response) error {
	eID := atomic.AddInt32(&s.eventID, 1)
	waitingCh := make(chan int32)
	s.eventChMap.Store(fmt.Sprint(eID), waitingCh)
	s.notificationCh <- notificationWrapper{ntype: beforeEvent, payload: fmt.Sprintf("%d\t%s\t%s\t%s", eID, request.OperationType, request.ResourceType, request.Object)}
	<-waitingCh
	*response = sieve.Response{Message: request.OperationType, Ok: true, Number: int(eID)}
	return nil
}

func (s *learnServer) NotifyLearnAfterIndexerWrite(request *sieve.NotifyLearnAfterIndexerWriteRequest, response *sieve.Response) error {
	s.notificationCh <- notificationWrapper{ntype: afterEvent, payload: fmt.Sprintf("%d", request.EventID)}
	*response = sieve.Response{Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnBeforeReconcile(request *sieve.NotifyLearnBeforeReconcileRequest, response *sieve.Response) error {
	recID := request.ControllerName + request.ControllerAddr
	waitingCh := make(chan int32)
	// We assume there is only one worker for one reconciler
	s.reconcileChMap.Store(recID, waitingCh)
	s.notificationCh <- notificationWrapper{ntype: beforeReconcile, payload: recID}
	<-waitingCh
	*response = sieve.Response{Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnAfterReconcile(request *sieve.NotifyLearnAfterReconcileRequest, response *sieve.Response) error {
	s.notificationCh <- notificationWrapper{ntype: afterReconcile, payload: request.ControllerName + request.ControllerAddr}
	*response = sieve.Response{Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnBeforeSideEffects(request *sieve.NotifyLearnBeforeSideEffectsRequest, response *sieve.Response) error {
	sID := atomic.AddInt32(&s.sideEffectID, 1)
	waitingCh := make(chan int32)
	s.sideEffectChMap.Store(fmt.Sprint(sID), waitingCh)
	s.notificationCh <- notificationWrapper{ntype: beforeSideEffect, payload: fmt.Sprintf("%d", sID)}
	<-waitingCh
	*response = sieve.Response{Message: request.SideEffectType, Ok: true, Number: int(sID)}
	return nil
}

func (s *learnServer) NotifyLearnAfterSideEffects(request *sieve.NotifyLearnAfterSideEffectsRequest, response *sieve.Response) error {
	s.notificationCh <- notificationWrapper{ntype: afterSideEffect, payload: fmt.Sprintf("%d\t%s\t%s\t%s\t%s\t%s", request.SideEffectID, request.SideEffectType, request.ResourceType, request.ReconcilerType, request.Error, request.Object)}
	*response = sieve.Response{Message: request.SideEffectType, Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnAfterOperatorGet(request *sieve.NotifyLearnAfterOperatorGetRequest, response *sieve.Response) error {
	s.notificationCh <- notificationWrapper{ntype: afterRead, payload: fmt.Sprintf("Get\t%s\t%s\t%s\t%s\t%s\t%s", request.ResourceType, request.Namespace, request.Name, request.ReconcilerType, request.Error, request.Object)}
	*response = sieve.Response{Message: "Get", Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnAfterOperatorList(request *sieve.NotifyLearnAfterOperatorListRequest, response *sieve.Response) error {
	s.notificationCh <- notificationWrapper{ntype: afterRead, payload: fmt.Sprintf("List\t%s\t%s\t%s\t%s", request.ResourceType, request.ReconcilerType, request.Error, request.ObjectList)}
	*response = sieve.Response{Message: "List", Ok: true}
	return nil
}

func (s *learnServer) coordinatingEvents() {
	for {
		select {
		case <-time.After(time.Second * time.Duration(s.rateLimiterInterval)):
			if s.rateLimiterEnabled {
				s.pollRateLimitedEventCh()
			}
		case nw := <-s.notificationCh:
			switch nw.ntype {
			case beforeReconcile:
				s.ongoingReconcileCnt += 1
				if _, ok := s.reconcileCntMap[nw.payload]; ok {
					s.reconcileCntMap[nw.payload] += 1
				} else {
					s.reconcileCntMap[nw.payload] = 0
				}
				if obj, ok := s.reconcileChMap.Load(nw.payload); ok {
					log.Printf("[SIEVE-BEFORE-RECONCILE]\t%s\t%d\n", nw.payload, s.reconcileCntMap[nw.payload])
					ch := obj.(chan int32)
					ch <- 0
				} else {
					log.Fatal("invalid object in reconcileChMap")
				}
			case afterReconcile:
				s.ongoingReconcileCnt -= 1
				if s.ongoingReconcileCnt == 0 {
					if s.rateLimiterEnabled {
						s.pollRateLimitedEventCh()
					}
				} else if s.ongoingReconcileCnt < 0 {
					log.Fatalf("reconcileCnt cannot be lower than 0: %d\n", s.ongoingReconcileCnt)
				}
				log.Printf("[SIEVE-AFTER-RECONCILE]\t%s\t%d\n", nw.payload, s.reconcileCntMap[nw.payload])
			case beforeSideEffect:
				sideEffectID := strings.Split(nw.payload, "\t")[0]
				if obj, ok := s.sideEffectChMap.Load(sideEffectID); ok {
					log.Printf("[SIEVE-BEFORE-WRITE]\t%s\n", nw.payload)
					ch := obj.(chan int32)
					ch <- 0
				} else {
					log.Fatal("invalid object in eventChMap")
				}
			case afterSideEffect:
				log.Printf("[SIEVE-AFTER-WRITE]\t%s\n", nw.payload)
			case beforeEvent:
				if !s.rateLimiterEnabled {
					eventID := strings.Split(nw.payload, "\t")[0]
					if obj, ok := s.eventChMap.Load(eventID); ok {
						// log.Printf("release event\n")
						log.Printf("[SIEVE-BEFORE-HEAR]\t%s\n", nw.payload)
						ch := obj.(chan int32)
						ch <- 0
					} else {
						log.Fatal("invalid object in eventChMap")
					}
				} else {
					s.rateLimitedEventCh <- nw
				}
			case afterEvent:
				log.Printf("[SIEVE-AFTER-HEAR]\t%s\n", nw.payload)
			case afterRead:
				log.Printf("[SIEVE-AFTER-READ]\t%s\n", nw.payload)
			default:
				log.Fatal("invalid notification type")
			}
		}
	}
}

func (s *learnServer) pollRateLimitedEventCh() {
	select {
	case nw := <-s.rateLimitedEventCh:
		eventID := strings.Split(nw.payload, "\t")[0]
		if obj, ok := s.eventChMap.Load(eventID); ok {
			log.Printf("ratelimiter release event\n")
			log.Printf("[SIEVE-BEFORE-HEAR]\t%s\n", nw.payload)
			ch := obj.(chan int32)
			ch <- 0
		} else {
			log.Fatal("invalid object in eventChMap")
		}
	default:
		log.Println("no event happening")
	}
}
