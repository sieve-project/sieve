package main

import (
	"log"
	"time"

	sonar "sonar.client/pkg/sonar"
)

func NewStalenessListener() *StalenessListener {
	server := &stalenessServer{
		apiserverHostname:    "kind-control-plane2",
		expectedResourceType: "cassandraoperator.instaclustr.com/v1alpha1, Kind=CassandraDataCenter",
	}
	listener := &StalenessListener{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

type StalenessListener struct {
	Server *stalenessServer
}

func (l *StalenessListener) Echo(request *sonar.EchoRequest, response *sonar.Response) error {
	*response = sonar.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *StalenessListener) WaitBeforeProcessEvent(request *sonar.WaitBeforeProcessEventRequest, response *sonar.Response) error {
	return l.Server.WaitBeforeProcessEvent(request, response)
}

type stalenessServer struct {
	apiserverHostname    string
	expectedResourceType string
}

func (s *stalenessServer) Start() {
	log.Println("start stalenessServer...")
}

func (s *stalenessServer) WaitBeforeProcessEvent(request *sonar.WaitBeforeProcessEventRequest, response *sonar.Response) error {
	log.Printf("RegisterQueue: EventType: %s, ResourceType: %s, Hostname: %s\n", request.EventType, request.ResourceType, request.Hostname)
	if request.EventType == "DELETED" && request.ResourceType == s.expectedResourceType && request.Hostname == s.apiserverHostname {
		log.Printf("Should sleep here...")
		time.Sleep(500 * time.Second)
	}
	*response = sonar.Response{Message: request.Hostname, Ok: true}
	return nil
}
