package main

import (
	"log"
	"net"
	"net/rpc"

	sieve "sieve.client"
)

// Sieve server runs on one of the kind-control-plane node (not in the pod).
// The server reads the config `server.yaml` and decides which listener to use.
// The listener will handle the RPC from sieve client (called by controllers or k8s components).
func main() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)
	log.Println("registering rpc server...")
	config := getConfig()

	switch config["stage"] {
	case sieve.LEARN:
		log.Println(sieve.LEARN)
		rpc.Register(NewLearnListener(config))

	case sieve.TEST:
		switch config["mode"] {
		case sieve.TIME_TRAVEL:
			log.Println(sieve.TIME_TRAVEL)
			rpc.Register(NewTimeTravelListener(config))
		case sieve.OBS_GAP:
			log.Println(sieve.OBS_GAP)
			rpc.Register(NewObsGapListener(config))
		case sieve.ATOM_VIO:
			log.Println(sieve.ATOM_VIO)
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
