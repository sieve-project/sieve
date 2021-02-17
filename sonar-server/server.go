package main

import (
	"log"
	"net"
	"net/rpc"

	sonar "sonar.client/pkg/sonar"
)

type listenerInterface interface {
	Echo(request *sonar.EchoRequest, response *sonar.Response) error
}

type serverInterface interface {
	Start()
}

func main() {
	log.Println("registering rpc server...")
	config := getConfig()
	switch config["mode"] {
	case "sparse-read":
		log.Println("sparse-read")
		rpc.Register(NewSparseReadListener(config))
	case "staleness":
		log.Println("staleness")
		rpc.Register(NewStalenessListener(config))
	default:
		log.Fatalf("Cannot recognize mode: %s\n", config["mode"])
	}

	log.Println("setting up connection...")
	addr, err := net.ResolveTCPAddr("tcp", ":12345")
	checkError(err)
	inbound, err := net.ListenTCP("tcp", addr)
	checkError(err)
	rpc.Accept(inbound)
}

func checkError(err error) {
	if err != nil {
		log.Fatalf("Fail due to error: %v\n", err)
	}
}
