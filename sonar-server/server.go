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

// Sonar server runs on one of the kind-control-plane node (not in the pod).
// The server reads the config `server.yaml` and decides which listener to use.
// The listener will handle the RPC from sonar client (called by controllers or k8s components).
func main() {
	log.Println("registering rpc server...")
	config := getConfig()
	switch config["mode"] {
	// sparse-read: The controller misses some of the events from apiserver
	// due to slow reconciliation. This is one type of observability gaps.
	case "sparse-read":
		log.Println("sparse-read")
		rpc.Register(NewSparseReadListener(config))
	// staleness: This actually refers to time-traveling.
	// There is some naming issue and I will fix it.
	// TODO: change name to time-traveling
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
