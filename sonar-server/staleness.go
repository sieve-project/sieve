package main

import (
	"log"
	"time"

	sonar "sonar.client/pkg/sonar"
)

func NewStalenessListener(config map[interface{}]interface{}) *StalenessListener {
	server := &stalenessServer{
		apiserverHostname:    config["apiserver"].(string),
		expectedResourceType: config["resource-type"].(string),
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
	log.Printf("WaitBeforeProcessEvent: EventType: %s, ResourceType: %s, Hostname: %s\n", request.EventType, request.ResourceType, request.Hostname)
	if request.EventType == "DELETED" && request.ResourceType == s.expectedResourceType && request.Hostname == s.apiserverHostname {
		log.Printf("Should sleep here...")
		time.Sleep(800 * time.Second)
		log.Printf("sleep over")
	}
	*response = sonar.Response{Message: request.Hostname, Ok: true}
	return nil
}
