package main

import (
	"fmt"
	"log"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	sieve "sieve.client"
)

func NewLearnListener() *LearnListener {
	config := getConfig()
	rateLimiterEnabledFromConfig := config["rateLimiterEnabled"].(bool)
	rateLimiterIntervalFromConfig := config["rateLimiterInterval"].(int)
	server := &learnServer{
		rateLimitedEventCh:    make(chan notificationWrapper, 500),
		eventID:               -1,
		sideEffectID:          -1,
		annotatedAPICallID:    -1,
		eventChMap:            sync.Map{},
		sideEffectChMap:       sync.Map{},
		nonK8sSideEffectChMap: sync.Map{},
		reconcileChMap:        sync.Map{},
		notificationCh:        make(chan notificationWrapper, 500),
		ongoingReconcileCnt:   0,
		reconcileCntMap:       map[string]int{},
		rateLimiterEnabled:    rateLimiterEnabledFromConfig,
		rateLimiterInterval:   rateLimiterIntervalFromConfig,
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

func (l *LearnListener) NotifyLearnBeforeControllerRecv(request *sieve.NotifyLearnBeforeControllerRecvRequest, response *sieve.Response) error {
	return l.Server.NotifyLearnBeforeControllerRecv(request, response)
}

func (l *LearnListener) NotifyLearnAfterControllerRecv(request *sieve.NotifyLearnAfterControllerRecvRequest, response *sieve.Response) error {
	return l.Server.NotifyLearnAfterControllerRecv(request, response)
}

func (l *LearnListener) NotifyLearnBeforeReconcile(request *sieve.NotifyLearnBeforeReconcileRequest, response *sieve.Response) error {
	return l.Server.NotifyLearnBeforeReconcile(request, response)
}

func (l *LearnListener) NotifyLearnAfterReconcile(request *sieve.NotifyLearnAfterReconcileRequest, response *sieve.Response) error {
	return l.Server.NotifyLearnAfterReconcile(request, response)
}

func (l *LearnListener) NotifyLearnBeforeControllerWrite(request *sieve.NotifyLearnBeforeControllerWriteRequest, response *sieve.Response) error {
	return l.Server.NotifyLearnBeforeControllerWrite(request, response)
}

func (l *LearnListener) NotifyLearnAfterControllerWrite(request *sieve.NotifyLearnAfterControllerWriteRequest, response *sieve.Response) error {
	return l.Server.NotifyLearnAfterControllerWrite(request, response)
}

func (l *LearnListener) NotifyLearnBeforeAnnotatedAPICall(request *sieve.NotifyLearnBeforeAnnotatedAPICallRequest, response *sieve.Response) error {
	return l.Server.NotifyLearnBeforeAnnotatedAPICall(request, response)
}

func (l *LearnListener) NotifyLearnAfterAnnotatedAPICall(request *sieve.NotifyLearnAfterAnnotatedAPICallRequest, response *sieve.Response) error {
	return l.Server.NotifyLearnAfterAnnotatedAPICall(request, response)
}

func (l *LearnListener) NotifyLearnAfterControllerGet(request *sieve.NotifyLearnAfterControllerGetRequest, response *sieve.Response) error {
	return l.Server.NotifyLearnAfterControllerGet(request, response)
}

func (l *LearnListener) NotifyLearnAfterControllerList(request *sieve.NotifyLearnAfterControllerListRequest, response *sieve.Response) error {
	return l.Server.NotifyLearnAfterControllerList(request, response)
}

type NotificationType int

const (
	beforeControllerReconcileForLearn NotificationType = iota
	afterControllerReconcileForLearn
	beforeControllerWriteForLearn
	afterControllerWriteForLearn
	beforeAnnotatedAPICallForLearn
	afterAnnotatedAPICallForLearn
	afterControllerReadForLearn
	beforeControllerRecvForLearn
	afterControllerRecvForLearn
)

type notificationWrapper struct {
	ntype   NotificationType
	payload string
}

type learnServer struct {
	rateLimitedEventCh    chan notificationWrapper
	eventID               int32
	sideEffectID          int32
	annotatedAPICallID    int32
	eventChMap            sync.Map
	sideEffectChMap       sync.Map
	nonK8sSideEffectChMap sync.Map
	reconcileChMap        sync.Map
	notificationCh        chan notificationWrapper
	ongoingReconcileCnt   int
	reconcileCntMap       map[string]int
	rateLimiterEnabled    bool
	rateLimiterInterval   int
}

func (s *learnServer) Start() {
	log.Println("start learnServer...")
	log.Printf("rateLimiterEnabled: %t\n", s.rateLimiterEnabled)
	go s.coordinatingEvents()
}

func (s *learnServer) NotifyLearnBeforeControllerRecv(request *sieve.NotifyLearnBeforeControllerRecvRequest, response *sieve.Response) error {
	eID := atomic.AddInt32(&s.eventID, 1)
	waitingCh := make(chan int32)
	s.eventChMap.Store(fmt.Sprint(eID), waitingCh)
	s.notificationCh <- notificationWrapper{ntype: beforeControllerRecvForLearn, payload: fmt.Sprintf("%d\t%s\t%s\t%s", eID, request.OperationType, request.ResourceType, request.Object)}
	<-waitingCh
	*response = sieve.Response{Message: request.OperationType, Ok: true, Number: int(eID)}
	return nil
}

func (s *learnServer) NotifyLearnAfterControllerRecv(request *sieve.NotifyLearnAfterControllerRecvRequest, response *sieve.Response) error {
	s.notificationCh <- notificationWrapper{ntype: afterControllerRecvForLearn, payload: fmt.Sprintf("%d", request.EventID)}
	*response = sieve.Response{Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnBeforeReconcile(request *sieve.NotifyLearnBeforeReconcileRequest, response *sieve.Response) error {
	recID := request.ReconcilerName
	// We assume there is only one worker for one reconciler
	if obj, ok := s.reconcileChMap.Load(recID); ok {
		if obj != nil {
			log.Fatal("object in reconcileChMap should be nil if exist when NotifyLearnBeforeReconcile")
		}
	}
	waitingCh := make(chan int32)
	s.reconcileChMap.Store(recID, waitingCh) // set the value to the channel when the reconcile starts
	s.notificationCh <- notificationWrapper{ntype: beforeControllerReconcileForLearn, payload: recID}
	<-waitingCh
	*response = sieve.Response{Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnAfterReconcile(request *sieve.NotifyLearnAfterReconcileRequest, response *sieve.Response) error {
	recID := request.ReconcilerName
	if obj, ok := s.reconcileChMap.Load(recID); ok {
		if obj == nil {
			log.Fatal("object in reconcileChMap should not be nil when NotifyLearnAfterReconcile")
		}
	} else {
		log.Fatal("object in reconcileChMap should exist when NotifyLearnAfterReconcile")
	}
	s.reconcileChMap.Store(recID, nil) // set value to nil when the reconcile ends
	s.notificationCh <- notificationWrapper{ntype: afterControllerReconcileForLearn, payload: recID}
	*response = sieve.Response{Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnBeforeControllerWrite(request *sieve.NotifyLearnBeforeControllerWriteRequest, response *sieve.Response) error {
	sID := atomic.AddInt32(&s.sideEffectID, 1)
	waitingCh := make(chan int32)
	s.sideEffectChMap.Store(fmt.Sprint(sID), waitingCh)
	s.notificationCh <- notificationWrapper{ntype: beforeControllerWriteForLearn, payload: fmt.Sprint(sID)}
	<-waitingCh
	*response = sieve.Response{Message: request.SideEffectType, Ok: true, Number: int(sID)}
	return nil
}

func (s *learnServer) NotifyLearnAfterControllerWrite(request *sieve.NotifyLearnAfterControllerWriteRequest, response *sieve.Response) error {
	s.notificationCh <- notificationWrapper{ntype: afterControllerWriteForLearn, payload: fmt.Sprintf("%d\t%s\t%s\t%s\t%s\t%s", request.SideEffectID, request.SideEffectType, request.ResourceType, request.ReconcilerType, request.Error, request.Object)}
	*response = sieve.Response{Message: request.SideEffectType, Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnBeforeAnnotatedAPICall(request *sieve.NotifyLearnBeforeAnnotatedAPICallRequest, response *sieve.Response) error {
	aID := atomic.AddInt32(&s.annotatedAPICallID, 1)
	waitingCh := make(chan int32)
	s.nonK8sSideEffectChMap.Store(fmt.Sprint(aID), waitingCh)
	s.notificationCh <- notificationWrapper{ntype: beforeAnnotatedAPICallForLearn, payload: fmt.Sprint(aID)}
	<-waitingCh
	*response = sieve.Response{Message: request.FunName, Ok: true, Number: int(aID)}
	return nil
}

func (s *learnServer) NotifyLearnAfterAnnotatedAPICall(request *sieve.NotifyLearnAfterAnnotatedAPICallRequest, response *sieve.Response) error {
	s.notificationCh <- notificationWrapper{ntype: afterAnnotatedAPICallForLearn, payload: fmt.Sprintf("%d\t%s\t%s\t%s\t%s\t%s", request.InvocationID, request.ModuleName, request.FilePath, request.ReceiverType, request.FunName, request.ReconcilerType)}
	*response = sieve.Response{Message: request.FunName, Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnAfterControllerGet(request *sieve.NotifyLearnAfterControllerGetRequest, response *sieve.Response) error {
	s.notificationCh <- notificationWrapper{ntype: afterControllerReadForLearn, payload: fmt.Sprintf("Get\t%t\t%s\t%s\t%s\t%s\t%s\t%s", request.FromCache, request.ResourceType, request.Namespace, request.Name, request.ReconcilerType, request.Error, request.Object)}
	*response = sieve.Response{Message: "Get", Ok: true}
	return nil
}

func (s *learnServer) NotifyLearnAfterControllerList(request *sieve.NotifyLearnAfterControllerListRequest, response *sieve.Response) error {
	s.notificationCh <- notificationWrapper{ntype: afterControllerReadForLearn, payload: fmt.Sprintf("List\t%t\t%s\t%s\t%s\t%s", request.FromCache, request.ResourceType, request.ReconcilerType, request.Error, request.ObjectList)}
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
			case beforeControllerReconcileForLearn:
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
			case afterControllerReconcileForLearn:
				s.ongoingReconcileCnt -= 1
				if s.ongoingReconcileCnt == 0 {
					if s.rateLimiterEnabled {
						s.pollRateLimitedEventCh()
					}
				} else if s.ongoingReconcileCnt < 0 {
					log.Fatalf("reconcileCnt cannot be lower than 0: %d\n", s.ongoingReconcileCnt)
				}
				log.Printf("[SIEVE-AFTER-RECONCILE]\t%s\t%d\n", nw.payload, s.reconcileCntMap[nw.payload])
			case beforeControllerWriteForLearn:
				if obj, ok := s.sideEffectChMap.Load(nw.payload); ok {
					log.Printf("[SIEVE-BEFORE-WRITE]\t%s\n", nw.payload)
					ch := obj.(chan int32)
					ch <- 0
				} else {
					log.Fatal("invalid object in eventChMap")
				}
			case afterControllerWriteForLearn:
				log.Printf("[SIEVE-AFTER-WRITE]\t%s\n", nw.payload)
			case beforeAnnotatedAPICallForLearn:
				if obj, ok := s.nonK8sSideEffectChMap.Load(nw.payload); ok {
					log.Printf("[SIEVE-BEFORE-ANNOTATED-API-INVOCATION]\t%s\n", nw.payload)
					ch := obj.(chan int32)
					ch <- 0
				} else {
					log.Fatal("invalid object in eventChMap")
				}
			case afterAnnotatedAPICallForLearn:
				log.Printf("[SIEVE-AFTER-ANNOTATED-API-INVOCATION]\t%s\n", nw.payload)
			case beforeControllerRecvForLearn:
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
			case afterControllerRecvForLearn:
				log.Printf("[SIEVE-AFTER-HEAR]\t%s\n", nw.payload)
			case afterControllerReadForLearn:
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
