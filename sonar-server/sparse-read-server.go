package main

import (
	"log"
	"sync"
	"time"

	sonar "sonar.client"
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

// NotifyBeforeMakeQ registers the queue for the desired controller name
func (l *SparseReadListener) NotifyBeforeMakeQ(request *sonar.NotifyBeforeMakeQRequest, response *sonar.Response) error {
	return l.Server.NotifyBeforeMakeQ(request, response)
}

// NotifyBeforeQAdd records each event pushed into the queue
func (l *SparseReadListener) NotifyBeforeQAdd(request *sonar.NotifyBeforeQAddRequest, response *sonar.Response) error {
	return l.Server.NotifyBeforeQAdd(request, response)
}

// NotifyBeforeReconcile blocks until reconcile is allowed
func (l *SparseReadListener) NotifyBeforeReconcile(request *sonar.NotifyBeforeReconcileRequest, response *sonar.Response) error {
	return l.Server.NotifyBeforeReconcile(request, response)
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

// NotifyBeforeMakeQ registers the queue for the desired controller name
func (s *sparseReadServer) NotifyBeforeMakeQ(request *sonar.NotifyBeforeMakeQRequest, response *sonar.Response) error {
	log.Printf("NotifyBeforeMakeQ: QueueId: %s and ControlleName: %s\n", request.QueueID, request.ControllerName)
	if _, loaded := s.controllerToQueue.LoadOrStore(request.ControllerName, request.QueueID); loaded {
		*response = sonar.Response{Message: "controller has already been registered", Ok: false}
		return nil
	}
	*response = sonar.Response{Message: request.QueueID, Ok: true}
	return nil
}

// NotifyBeforeQAdd records each event pushed into the queue
func (s *sparseReadServer) NotifyBeforeQAdd(request *sonar.NotifyBeforeQAddRequest, response *sonar.Response) error {
	log.Printf("NotifyBeforeQAdd: QueueId: %s\n", request.QueueID)
	s.eventCh <- request.QueueID
	*response = sonar.Response{Message: request.QueueID, Ok: true}
	return nil
}

// NotifyBeforeReconcile blocks until reconcile is allowed
func (s *sparseReadServer) NotifyBeforeReconcile(request *sonar.NotifyBeforeReconcileRequest, response *sonar.Response) error {
	log.Printf("NotifyBeforeReconcile: ControllerName: %s\n", request.ControllerName)
	if request.ControllerName != s.controllerName {
		log.Printf("%s != %s (expected), no need to wait\n", request.ControllerName, s.controllerName)
		*response = sonar.Response{Message: request.ControllerName, Ok: true}
		return nil
	}
	// reconcile needs to wait for 10s when queuesAreCold is false.
	// queuesAreCold will only become true when no NotifyBeforeQAdd comes for 10s.
	// This policy is heavily timing sensitive
	// TODO: try to eliminate the indeterminism here
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

// receivingAllQueuedEvents runs in a goroutine.
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
