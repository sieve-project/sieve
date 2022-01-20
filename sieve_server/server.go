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
		learnedMask, configuredMask := getMask()
		switch config["mode"] {
		case sieve.STALE_STATE:
			log.Println(sieve.STALE_STATE)
			rpc.Register(NewTimeTravelListener(config, learnedMask, configuredMask))
		case sieve.UNOBSR_STATE:
			log.Println(sieve.UNOBSR_STATE)
			rpc.Register(NewObsGapListener(config, learnedMask, configuredMask))
		case sieve.INTERMEDIATE_STATE:
			log.Println(sieve.INTERMEDIATE_STATE)
			rpc.Register(NewAtomVioListener(config, learnedMask, configuredMask))

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
