package main

import (
	"log"
	"net"
	"net/rpc"
	"os"

	sieve "sieve.client"
)

// Sieve server runs on one of the kind-control-plane node (not in the pod).
// The server reads the config `server.yaml` and decides which listener to use.
// The listener will handle the RPC from sieve client (called by controllers or k8s components).
func main() {
	log.SetFlags(log.LstdFlags | log.Lshortfile | log.Lmicroseconds)
	log.Println("registering rpc server...")
	args := os.Args
	phase := args[1]
	switch phase {
	case sieve.LEARN:
		rpc.Register(NewLearnListener())
	case sieve.TEST:
		rpc.Register(NewTestCoordinator())
	default:
		log.Fatalf("Cannot recognize mode: %s\n", phase)
	}
	log.Println("setting up connection...")
	addr, err := net.ResolveTCPAddr("tcp", ":12345")
	checkError(err)
	inbound, err := net.ListenTCP("tcp", addr)
	checkError(err)
	rpc.Accept(inbound)
}
