package sonar

import (
	"fmt"
	"io/ioutil"
	"net/rpc"
	"os"
	"time"

	"log"

	"gopkg.in/yaml.v2"
)

var hostPort string = "kind-control-plane:12345"
var connectionError string = "[sonar] connectionError"
var replyError string = "[sonar] replyError"
var hostError string = "[sonar] hostError"
var configError string = "[sonar] configError"
var config map[interface{}]interface{} = nil
var sparseRead string = "sparse-read"
var staleness string = "staleness"

func checkMode(mode string) bool {
	if config == nil {
		config, _ = getConfig()
	}
	if config == nil {
		return false
	}
	return config["mode"] == mode
}

func newClient() (*rpc.Client, error) {
	client, err := rpc.Dial("tcp", hostPort)
	if err != nil {
		log.Printf("[sonar] error in setting up connection to %s due to %v\n", hostPort, err)
		return nil, err
	}
	return client, nil
}

func getConfig() (map[interface{}]interface{}, error) {
	data, err := ioutil.ReadFile("/sonar.yaml")
	if err != nil {
		return nil, err
	}
	m := make(map[interface{}]interface{})
	err = yaml.Unmarshal([]byte(data), &m)
	if err != nil {
		return nil, err
	}
	log.Printf("[sonar] config:\n%v\n", m)
	return m, nil
}

func printError(err error, text string) {
	log.Printf("[sonar][error] %s due to: %v \n", text, err)
}

func checkResponse(response Response, reqName string) {
	if response.Ok {
		log.Printf("[sonar][%s] receives good response: %s\n", reqName, response.Message)
	} else {
		log.Printf("[sonar][error][%s] receives bad response: %s\n", reqName, response.Message)
	}
}

// RegisterQueue is invoked before controller creating a queue
// RegisterQueue lets the server know which controller creates which queue,
// this piece of information is not utilized by server so far.
func RegisterQueue(queue interface{}, controllerName string) {
	if !checkMode(sparseRead) {
		return
	}
	log.Printf("[sonar][RegisterQueue] queue: %p, controllerName: %s\n", queue, controllerName)
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	queueID := fmt.Sprintf("%p", queue)
	request := &RegisterQueueRequest{
		QueueID:        queueID,
		ControllerName: controllerName,
	}
	var response Response
	err = client.Call("SparseReadListener.RegisterQueue", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "RegisterQueue")
	client.Close()
}

// PushIntoQueue is invoked before controller calling q.Add
// PushIntoQueue lets the server know how busy the queues and controller are.
func PushIntoQueue(queue interface{}) {
	if !checkMode(sparseRead) {
		return
	}
	log.Printf("[sonar][PushIntoQueue] queue: %p\n", queue)
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	queueID := fmt.Sprintf("%p", queue)
	request := &PushIntoQueueRequest{
		QueueID: queueID,
	}
	var response Response
	err = client.Call("SparseReadListener.PushIntoQueue", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "PushIntoQueue")
	client.Close()
}

// WaitBeforeReconcile is invoked before controller calling Reconcile()
// WaitBeforeReconcile lets controller know a reconcile is going to happen,
// and the controller should decide whether to delay it.
func WaitBeforeReconcile(controllerName string) {
	if !checkMode(sparseRead) {
		return
	}
	log.Printf("[sonar][WaitBeforeReconcile] controllerName: %s\n", controllerName)
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	request := &WaitBeforeReconcileRequest{
		ControllerName: controllerName,
	}
	var response Response
	err = client.Call("SparseReadListener.WaitBeforeReconcile", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "WaitBeforeReconcile")
	client.Close()
}

// WaitBeforeProcessEvent is invoked before apiserver calling processEvent()
// WaitBeforeProcessEvent lets the server know the apiserver is going to process an event from etcd,
// the server should decide whether to freeze the apiserver or restart the controller.
func WaitBeforeProcessEvent(eventType, resourceType string) {
	if !checkMode(staleness) {
		// log.Printf("[sonar][NOT-ready][WaitBeforeProcessEvent] eventType: %s, resourceType: %s\n", eventType, resourceType)
		return
	}
	if resourceType != config["freeze-resource-type"] && resourceType != config["restart-resource-type"] {
		return
	}
	log.Printf("[sonar][WaitBeforeProcessEvent] eventType: %s, resourceType: %s\n", eventType, resourceType)
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	hostname, err := os.Hostname()
	if err != nil {
		printError(err, hostError)
		return
	}
	request := &WaitBeforeProcessEventRequest{
		EventType:    eventType,
		ResourceType: resourceType,
		Hostname:     hostname,
	}
	var response Response
	err = client.Call("StalenessListener.WaitBeforeProcessEvent", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "WaitBeforeProcessEvent")
	if response.Wait != 0 {
		log.Printf("[sonar][WaitBeforeProcessEvent] should sleep for %d seconds here", response.Wait)
		time.Sleep(time.Duration(response.Wait) * time.Second)
	}
	client.Close()
}
