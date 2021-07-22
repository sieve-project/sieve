package main

import (
	"log"

	sonar "sonar.client"
)

func NewAtomicListener(config map[interface{}]interface{}) *AtomicListener {
	server := &atomicServer{}
	listener := &AtomicListener{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

type AtomicListener struct {
	Server *atomicServer
}

func (l *AtomicListener) Echo(request *sonar.EchoRequest, response *sonar.Response) error {
	*response = sonar.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *AtomicListener) NotifyAtomicSideEffects(request *sonar.NotifyAtomicSideEffectsRequest, response *sonar.Response) error {
	return l.Server.NotifyAtomicSideEffects(request, response)
}

type atomicServer struct {
}

func (s *atomicServer) Start() {
	log.Println("start atomicServer...")
	// go s.coordinatingEvents()
}

func (s *atomicServer) NotifyAtomicSideEffects(request *sonar.NotifyAtomicSideEffectsRequest, response *sonar.Response) error {
	name, namespace := extractNameNamespace(request.Object)
	log.Printf("[SONAR-SIDE-EFFECT]\t%s\t%s\t%s\t%s\t%s\n", request.SideEffectType, request.ResourceType, namespace, name, request.Error)
	*response = sonar.Response{Message: request.SideEffectType, Ok: true}
	return nil
}
