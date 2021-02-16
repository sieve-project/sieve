package sonar

import (
	"fmt"
	"net/rpc"
	"os"

	"log"
)

var hostPort string = "kind-control-plane:12345"
var connectionError string = "[sonar] connectionError"
var replyError string = "[sonar] replyError"
var hostError string = "[sonar] hostError"
var enableSparseRead bool = checkSparseRead()
var enableStaleness bool = checkStaleness()

func checkSparseRead() bool {
	return os.Getenv("MODE") == "sparse-read"
}

func checkStaleness() bool {
	return os.Getenv("MODE") == "staleness"
}

func newClient() (*rpc.Client, error) {
	client, err := rpc.Dial("tcp", hostPort)
	if err != nil {
		log.Printf("[sonar] error in setting up connection to %s due to %v\n", hostPort, err)
		return nil, err
	}
	return client, nil
}

func checkError(err error, text string) {
	if err != nil {
		log.Fatalf("[sonar] %s due to: %v \n", text, err)
	}
}

func checkResponse(response Response, reqName string) {
	if response.Ok {
		log.Printf("[sonar][%s] receives good response: %s\n", reqName, response.Message)
	} else {
		log.Fatalf("[sonar][%s] receives bad response: %s\n", reqName, response.Message)
	}
}

// RegisterQueue registers the queue with the controller to the server
func RegisterQueue(queue interface{}, controllerName string) {
	if !enableSparseRead {
		return
	}
	log.Printf("[sonar][RegisterQueue] queue: %p, controllerName: %s\n", queue, controllerName)
	client, err := newClient()
	checkError(err, connectionError)
	queueID := fmt.Sprintf("%p", queue)
	request := &RegisterQueueRequest{
		QueueID:        queueID,
		ControllerName: controllerName,
	}
	var response Response
	err = client.Call("SparseReadListener.RegisterQueue", request, &response)
	checkError(err, replyError)
	checkResponse(response, "RegisterQueue")
	client.Close()
}

// PushIntoQueue notifies the server that one event is pushed into queue
func PushIntoQueue(queue interface{}) {
	if !enableSparseRead {
		return
	}
	log.Printf("[sonar][PushIntoQueue] queue: %p\n", queue)
	client, err := newClient()
	checkError(err, connectionError)
	queueID := fmt.Sprintf("%p", queue)
	request := &PushIntoQueueRequest{
		QueueID: queueID,
	}
	var response Response
	err = client.Call("SparseReadListener.PushIntoQueue", request, &response)
	checkError(err, replyError)
	checkResponse(response, "PushIntoQueue")
	client.Close()
}

// WaitBeforeReconcile waits until controller is allowed to reconcile
func WaitBeforeReconcile(controllerName string) {
	if !enableSparseRead {
		return
	}
	log.Printf("[sonar][WaitBeforeReconcile] controllerName: %s\n", controllerName)
	client, err := newClient()
	checkError(err, connectionError)
	request := &WaitBeforeReconcileRequest{
		ControllerName: controllerName,
	}
	var response Response
	err = client.Call("SparseReadListener.WaitBeforeReconcile", request, &response)
	checkError(err, replyError)
	checkResponse(response, "WaitBeforeReconcile")
	client.Close()
}

func getHostname() string {
	hostname, err := os.Hostname()
	checkError(err, hostError)
	return hostname
}

func WaitBeforeProcessEvent(eventType, resourceType string) {
	if !enableStaleness {
		return
	}
	log.Printf("[sonar][WaitBeforeProcessEvent] eventType: %s, resourceType: %s\n", eventType, resourceType)
	client, err := newClient()
	checkError(err, connectionError)
	request := &WaitBeforeProcessEventRequest{
		EventType:    eventType,
		ResourceType: resourceType,
		Hostname:     getHostname(),
	}
	var response Response
	err = client.Call("StalenessListener.WaitBeforeProcessEvent", request, &response)
	checkError(err, replyError)
	checkResponse(response, "WaitBeforeProcessEvent")
	client.Close()
}
