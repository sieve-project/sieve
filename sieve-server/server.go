package main

import (
	"log"
	"net"
	"net/rpc"
)

// Sieve server runs on one of the kind-control-plane node (not in the pod).
// The server reads the config `server.yaml` and decides which listener to use.
// The listener will handle the RPC from sieve client (called by controllers or k8s components).
func main() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	log.Println("registering rpc server...")
	config := getConfig()

	switch config["stage"] {
	case LEARN:
		log.Println(LEARN)
		rpc.Register(NewLearnListener(config))

	case TEST:
		switch config["mode"] {
		case TIME_TRAVEL:
			log.Println(TIME_TRAVEL)
			rpc.Register(NewTimeTravelListener(config))
		case OBS_GAP:
			log.Println(OBS_GAP)
			rpc.Register(NewObsGapListener(config))
		case ATOM_VIO:
			log.Println(ATOM_VIO)
			rpc.Register(NewAtomVioListener(config))

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
