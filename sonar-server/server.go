package main

import (
	"log"
	"net"
	"net/rpc"

	sonar "sonar.client"
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
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	log.Println("registering rpc server...")
	config := getConfig()

	switch config["stage"] {
	case "learn":
		log.Println("learn")
		rpc.Register(NewLearnListener(config))

	case "test":
		switch config["mode"] {
		// time-travel: Replay the partial history to the controller by
		// injecting delay to apiservers and restarting the controllers.
		case "time-travel":
			log.Println("time-travel")
			rpc.Register(NewTimeTravelListener(config))
		// obs-gap: Observabiliy Gaps
		case "obs-gap":
			log.Println("obs-gap")
			rpc.Register(NewObsGapListener(config))
		// atomic: atomic side effect during reconcile
		case "atomic":
			log.Println("atomic")
			rpc.Register(NewAtomicListener(config))

		default:
			log.Fatalf("Cannot recognize mode: %s\n", config["mode"])
		}

	default:
		log.Fatalf("Cannot recognize stage: %s\n", config["stage"])
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

func extractNameNamespace(Object string) (string, string) {
	objectMap := strToMap(Object)
	name := ""
	namespace := ""
	if _, ok := objectMap["metadata"]; ok {
		if metadataMap, ok := objectMap["metadata"].(map[string]interface{}); ok {
			if _, ok := metadataMap["name"]; ok {
				name = metadataMap["name"].(string)
			}
			if _, ok := metadataMap["namespace"]; ok {
				namespace = metadataMap["namespace"].(string)
			}
		}
	}
	return name, namespace
}
