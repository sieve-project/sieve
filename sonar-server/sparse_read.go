package main

import (
	"log"
	"sync"
	"time"

	sonar "sonar.client/pkg/sonar"
)

func NewSparseReadListener(config map[interface{}]interface{}) *SparseReadListener {
	server := &sparseReadServer{
		controllerName:    config["controller-name"].(string),
		controllerToQueue: sync.Map{},
		eventCh:           make(chan string, 100),
		queuesAreCold:     true,
	}
	listener := &SparseReadListener{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

type SparseReadListener struct {
	Server *sparseReadServer
}

func (l *SparseReadListener) Echo(request *sonar.EchoRequest, response *sonar.Response) error {
	*response = sonar.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

// RegisterQueue registers the queue for the desired controller name
func (l *SparseReadListener) RegisterQueue(request *sonar.RegisterQueueRequest, response *sonar.Response) error {
	return l.Server.RegisterQueue(request, response)
}

// PushIntoQueue records each event pushed into the queue
func (l *SparseReadListener) PushIntoQueue(request *sonar.PushIntoQueueRequest, response *sonar.Response) error {
	return l.Server.PushIntoQueue(request, response)
}

// WaitBeforeReconcile blocks until reconcile is allowed
func (l *SparseReadListener) WaitBeforeReconcile(request *sonar.WaitBeforeReconcileRequest, response *sonar.Response) error {
	return l.Server.WaitBeforeReconcile(request, response)
}

type sparseReadServer struct {
	controllerName    string
	controllerToQueue sync.Map
	eventCh           chan string
	queuesAreCold     bool
}

func (s *sparseReadServer) Start() {
	log.Println("start sparseReadServer...")
	go s.receivingAllQueuedEvents()
}

// RegisterQueue registers the queue for the desired controller name
func (s *sparseReadServer) RegisterQueue(request *sonar.RegisterQueueRequest, response *sonar.Response) error {
	log.Printf("RegisterQueue: QueueId: %s and ControlleName: %s\n", request.QueueID, request.ControllerName)
	if _, loaded := s.controllerToQueue.LoadOrStore(request.ControllerName, request.QueueID); loaded {
		*response = sonar.Response{Message: "controller has already been registered", Ok: false}
		return nil
	}
	*response = sonar.Response{Message: request.QueueID, Ok: true}
	return nil
}

// PushIntoQueue records each event pushed into the queue
func (s *sparseReadServer) PushIntoQueue(request *sonar.PushIntoQueueRequest, response *sonar.Response) error {
	log.Printf("PushIntoQueue: QueueId: %s\n", request.QueueID)
	s.eventCh <- request.QueueID
	*response = sonar.Response{Message: request.QueueID, Ok: true}
	return nil
}

// WaitBeforeReconcile blocks until reconcile is allowed
func (s *sparseReadServer) WaitBeforeReconcile(request *sonar.WaitBeforeReconcileRequest, response *sonar.Response) error {
	log.Printf("WaitBeforeReconcile: ControllerName: %s\n", request.ControllerName)
	if request.ControllerName != s.controllerName {
		log.Printf("%s != %s (expected), no need to wait\n", request.ControllerName, s.controllerName)
		*response = sonar.Response{Message: request.ControllerName, Ok: true}
		return nil
	}
	if s.queuesAreCold {
		log.Println("No need to wait since queuesAreCold is true")
		*response = sonar.Response{Message: request.ControllerName, Ok: true}
		return nil
	}
	log.Println("sleep for 10 seconds since events are still coming")
	time.Sleep(10 * time.Second)
	*response = sonar.Response{Message: request.ControllerName, Ok: true}
	return nil
}

func (s *sparseReadServer) receivingAllQueuedEvents() {
	for {
		select {
		case <-s.eventCh:
			s.queuesAreCold = false
		case <-time.After(time.Second * 10):
			s.queuesAreCold = true
		}
	}
}
