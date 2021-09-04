package main

import (
	"fmt"
	"log"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	sonar "sonar.client"
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
		eventChMap:          sync.Map{},
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

func (l *LearnListener) Echo(request *sonar.EchoRequest, response *sonar.Response) error {
	*response = sonar.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *LearnListener) NotifyLearnBeforeIndexerWrite(request *sonar.NotifyLearnBeforeIndexerWriteRequest, response *sonar.Response) error {
	return l.Server.NotifyLearnBeforeIndexerWrite(request, response)
}

func (l *LearnListener) NotifyLearnAfterIndexerWrite(request *sonar.NotifyLearnAfterIndexerWriteRequest, response *sonar.Response) error {
	return l.Server.NotifyLearnAfterIndexerWrite(request, response)
}

func (l *LearnListener) NotifyLearnBeforeReconcile(request *sonar.NotifyLearnBeforeReconcileRequest, response *sonar.Response) error {
	return l.Server.NotifyLearnBeforeReconcile(request, response)
}

func (l *LearnListener) NotifyLearnAfterReconcile(request *sonar.NotifyLearnAfterReconcileRequest, response *sonar.Response) error {
	return l.Server.NotifyLearnAfterReconcile(request, response)
}

func (l *LearnListener) NotifyLearnSideEffects(request *sonar.NotifyLearnSideEffectsRequest, response *sonar.Response) error {
	return l.Server.NotifyLearnSideEffects(request, response)
}

func (l *LearnListener) NotifyLearnCacheGet(request *sonar.NotifyLearnCacheGetRequest, response *sonar.Response) error {
	return l.Server.NotifyLearnCacheGet(request, response)
}

func (l *LearnListener) NotifyLearnCacheList(request *sonar.NotifyLearnCacheListRequest, response *sonar.Response) error {
	return l.Server.NotifyLearnCacheList(request, response)
}

type NotificationType int

const (
	reconcileStart NotificationType = iota
	reconcileFinish
	sideEffect
	cacheRead
	eventArrival
	eventApplied
)

type notificationWrapper struct {
	ntype   NotificationType
	payload string
}

type learnServer struct {
	rateLimitedEventCh  chan notificationWrapper
	eventID             int32
	eventChMap          sync.Map
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

func (s *learnServer) NotifyLearnBeforeIndexerWrite(request *sonar.NotifyLearnBeforeIndexerWriteRequest, response *sonar.Response) error {
	eID := atomic.AddInt32(&s.eventID, 1)
	waitingCh := make(chan int32)
	s.eventChMap.Store(fmt.Sprint(eID), waitingCh)
	s.notificationCh <- notificationWrapper{ntype: eventArrival, payload: fmt.Sprintf("%d\t%s\t%s\t%s", eID, request.OperationType, request.ResourceType, request.Object)}
	<-waitingCh
	*response = sonar.Response{Message: request.OperationType, Ok: true, Number: int(eID)}
	return nil
}

func (s *learnServer) NotifyLearnAfterIndexerWrite(request *sonar.NotifyLearnAfterIndexerWriteRequest, response *sonar.Response) error {
	s.notificationCh <- notificationWrapper{ntype: eventApplied, payload: fmt.Sprintf("%d", request.EventID)}
	*response = sonar.Response{Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnBeforeReconcile(request *sonar.NotifyLearnBeforeReconcileRequest, response *sonar.Response) error {
	recID := request.ControllerName
	waitingCh := make(chan int32)
	// use LoadOrStore here because the same controller may have mulitple workers concurrently running reconcile
	// So the same recID may be stored before
	obj, _ := s.reconcileChMap.LoadOrStore(recID, waitingCh)
	waitingCh = obj.(chan int32)
	s.notificationCh <- notificationWrapper{ntype: reconcileStart, payload: recID}
	<-waitingCh
	*response = sonar.Response{Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnAfterReconcile(request *sonar.NotifyLearnAfterReconcileRequest, response *sonar.Response) error {
	s.notificationCh <- notificationWrapper{ntype: reconcileFinish, payload: request.ControllerName}
	*response = sonar.Response{Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnSideEffects(request *sonar.NotifyLearnSideEffectsRequest, response *sonar.Response) error {
	rtype := request.ResourceType
	name, namespace := extractNameNamespace(request.Object)
	s.notificationCh <- notificationWrapper{ntype: sideEffect, payload: request.SideEffectType + "\t" + rtype + "\t" + namespace + "\t" + name + "\t" + request.Error}
	*response = sonar.Response{Message: request.SideEffectType, Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnCacheGet(request *sonar.NotifyLearnCacheGetRequest, response *sonar.Response) error {
	s.notificationCh <- notificationWrapper{ntype: cacheRead, payload: fmt.Sprintf("Get\t%s\t%s\t%s\t%s", request.ResourceType, request.Namespace, request.Name, request.Error)}
	*response = sonar.Response{Message: "Get", Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnCacheList(request *sonar.NotifyLearnCacheListRequest, response *sonar.Response) error {
	s.notificationCh <- notificationWrapper{ntype: cacheRead, payload: fmt.Sprintf("List\t%s\t%s", request.ResourceType, request.Error)}
	*response = sonar.Response{Message: "List", Ok: true}
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
			case reconcileStart:
				s.ongoingReconcileCnt += 1
				if _, ok := s.reconcileCntMap[nw.payload]; ok {
					s.reconcileCntMap[nw.payload] += 1
				} else {
					s.reconcileCntMap[nw.payload] = 0
				}
				if obj, ok := s.reconcileChMap.Load(nw.payload); ok {
					log.Printf("[SONAR-START-RECONCILE]\t%s\t%d\n", nw.payload, s.reconcileCntMap[nw.payload])
					ch := obj.(chan int32)
					ch <- 0
				} else {
					log.Fatal("invalid object in reconcileChMap")
				}
			case reconcileFinish:
				s.ongoingReconcileCnt -= 1
				if s.ongoingReconcileCnt == 0 {
					if s.rateLimiterEnabled {
						s.pollRateLimitedEventCh()
					}
				} else if s.ongoingReconcileCnt < 0 {
					log.Fatalf("reconcileCnt cannot be lower than 0: %d\n", s.ongoingReconcileCnt)
				}
				log.Printf("[SONAR-FINISH-RECONCILE]\t%s\t%d\n", nw.payload, s.reconcileCntMap[nw.payload])
			case sideEffect:
				if s.ongoingReconcileCnt > 0 {
					log.Printf("[SONAR-SIDE-EFFECT]\t%s\n", nw.payload)
				}
			case eventArrival:
				if !s.rateLimiterEnabled {
					eventID := strings.Split(nw.payload, "\t")[0]
					if obj, ok := s.eventChMap.Load(eventID); ok {
						log.Printf("release event\n")
						log.Printf("[SONAR-EVENT]\t%s\n", nw.payload)
						ch := obj.(chan int32)
						ch <- 0
					} else {
						log.Fatal("invalid object in eventChMap")
					}
				} else {
					s.rateLimitedEventCh <- nw
				}
			case eventApplied:
				log.Printf("[SONAR-EVENT-APPLIED]\t%s\n", nw.payload)
			case cacheRead:
				log.Printf("[SONAR-CACHE-READ]\t%s\n", nw.payload)
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
			log.Printf("[SONAR-EVENT]\t%s\n", nw.payload)
			ch := obj.(chan int32)
			ch <- 0
		} else {
			log.Fatal("invalid object in eventChMap")
		}
	default:
		log.Println("no event happening")
	}
}
