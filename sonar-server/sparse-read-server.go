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

// NotifySparseReadBeforeMakeQ registers the queue for the desired controller name
func (l *SparseReadListener) NotifySparseReadBeforeMakeQ(request *sonar.NotifySparseReadBeforeMakeQRequest, response *sonar.Response) error {
	return l.Server.NotifySparseReadBeforeMakeQ(request, response)
}

// NotifySparseReadBeforeQAdd records each event pushed into the queue
func (l *SparseReadListener) NotifySparseReadBeforeQAdd(request *sonar.NotifySparseReadBeforeQAddRequest, response *sonar.Response) error {
	return l.Server.NotifySparseReadBeforeQAdd(request, response)
}

// NotifySparseReadBeforeReconcile blocks until reconcile is allowed
func (l *SparseReadListener) NotifySparseReadBeforeReconcile(request *sonar.NotifySparseReadBeforeReconcileRequest, response *sonar.Response) error {
	return l.Server.NotifySparseReadBeforeReconcile(request, response)
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

// NotifySparseReadBeforeMakeQ registers the queue for the desired controller name
func (s *sparseReadServer) NotifySparseReadBeforeMakeQ(request *sonar.NotifySparseReadBeforeMakeQRequest, response *sonar.Response) error {
	log.Printf("NotifySparseReadBeforeMakeQ: QueueId: %s and ControlleName: %s\n", request.QueueID, request.ControllerName)
	if _, loaded := s.controllerToQueue.LoadOrStore(request.ControllerName, request.QueueID); loaded {
		*response = sonar.Response{Message: "controller has already been registered", Ok: false}
		return nil
	}
	*response = sonar.Response{Message: request.QueueID, Ok: true}
	return nil
}

// NotifySparseReadBeforeQAdd records each event pushed into the queue
func (s *sparseReadServer) NotifySparseReadBeforeQAdd(request *sonar.NotifySparseReadBeforeQAddRequest, response *sonar.Response) error {
	log.Printf("NotifySparseReadBeforeQAdd: QueueId: %s\n", request.QueueID)
	s.eventCh <- request.QueueID
	*response = sonar.Response{Message: request.QueueID, Ok: true}
	return nil
}

// NotifySparseReadBeforeReconcile blocks until reconcile is allowed
func (s *sparseReadServer) NotifySparseReadBeforeReconcile(request *sonar.NotifySparseReadBeforeReconcileRequest, response *sonar.Response) error {
	log.Printf("NotifySparseReadBeforeReconcile: ControllerName: %s\n", request.ControllerName)
	if request.ControllerName != s.controllerName {
		log.Printf("%s != %s (expected), no need to wait\n", request.ControllerName, s.controllerName)
		*response = sonar.Response{Message: request.ControllerName, Ok: true}
		return nil
	}
	// reconcile needs to wait for 10s when queuesAreCold is false.
	// queuesAreCold will only become true when no NotifySparseReadBeforeQAdd comes for 10s.
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
