package sonar

import (
	"fmt"
	"io/ioutil"
	"net/rpc"
	"os"
	"time"
	"encoding/json"
	"log"

	"gopkg.in/yaml.v2"
)

var hostPort string = "kind-control-plane:12345"
var connectionError string = "[sonar] connectionError"
var replyError string = "[sonar] replyError"
var hostError string = "[sonar] hostError"
var configError string = "[sonar] configError"
var jsonError string = "[sonar jsonError]"
var config map[interface{}]interface{} = nil
var sparseRead string = "sparse-read"
var timeTravel string = "time-travel"
var learn string = "learn"

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

// NotifyBeforeMakeQ is invoked before controller creating a queue
// NotifyBeforeMakeQ lets the server know which controller creates which queue,
// this piece of information is not utilized by server so far.
func NotifyBeforeMakeQ(queue interface{}, controllerName string) {
	if !checkMode(sparseRead) {
		return
	}
	log.Printf("[sonar][NotifyBeforeMakeQ] queue: %p, controllerName: %s\n", queue, controllerName)
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	queueID := fmt.Sprintf("%p", queue)
	request := &NotifyBeforeMakeQRequest{
		QueueID:        queueID,
		ControllerName: controllerName,
	}
	var response Response
	err = client.Call("SparseReadListener.NotifyBeforeMakeQ", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyBeforeMakeQ")
	client.Close()
}

// NotifyBeforeQAdd is invoked before controller calling q.Add
// NotifyBeforeQAdd lets the server know how busy the queues and controller are.
func NotifyBeforeQAdd(queue interface{}) {
	if !checkMode(sparseRead) {
		return
	}
	log.Printf("[sonar][NotifyBeforeQAdd] queue: %p\n", queue)
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	queueID := fmt.Sprintf("%p", queue)
	request := &NotifyBeforeQAddRequest{
		QueueID: queueID,
	}
	var response Response
	err = client.Call("SparseReadListener.NotifyBeforeQAdd", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyBeforeQAdd")
	client.Close()
}

// NotifyBeforeReconcile is invoked before controller calling Reconcile()
// NotifyBeforeReconcile lets controller know a reconcile is going to happen,
// and the controller should decide whether to delay it.
func NotifyBeforeReconcile(controllerName string) {
	if !checkMode(sparseRead) {
		return
	}
	log.Printf("[sonar][NotifyBeforeReconcile] controllerName: %s\n", controllerName)
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	request := &NotifyBeforeReconcileRequest{
		ControllerName: controllerName,
	}
	var response Response
	err = client.Call("SparseReadListener.NotifyBeforeReconcile", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyBeforeReconcile")
	client.Close()
}

// NotifyBeforeProcessEvent is invoked before apiserver calling processEvent()
// NotifyBeforeProcessEvent lets the server know the apiserver is going to process an event from etcd,
// the server should decide whether to freeze the apiserver or restart the controller.
func NotifyBeforeProcessEvent(eventType, resourceType string) {
	if !checkMode(timeTravel) {
		// log.Printf("[sonar][NOT-ready][NotifyBeforeProcessEvent] eventType: %s, resourceType: %s\n", eventType, resourceType)
		return
	}
	log.Printf("[sonar][test][NotifyBeforeProcessEvent] eventType: %s, resourceType: %s\n", eventType, resourceType)
	if resourceType != config["freeze-resource-type"] && resourceType != config["restart-resource-type"] {
		return
	}
	log.Printf("[sonar][NotifyBeforeProcessEvent] eventType: %s, resourceType: %s\n", eventType, resourceType)
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
	request := &NotifyBeforeProcessEventRequest{
		EventType:    eventType,
		ResourceType: resourceType,
		Hostname:     hostname,
	}
	var response Response
	err = client.Call("TimeTravelListener.NotifyBeforeProcessEvent", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyBeforeProcessEvent")
	if response.Wait != 0 {
		log.Printf("[sonar][NotifyBeforeProcessEvent] should sleep for %d seconds here", response.Wait)
		time.Sleep(time.Duration(response.Wait) * time.Second)
	}
	client.Close()
}

func NotifyLearnBeforeIndexerWrite(operationType string, object interface{}) {
	if !checkMode(learn) {
		return
	}
	log.Printf("[sonar][NotifyLearnBeforeIndexerWrite] operationType: %s\n", operationType)
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, jsonError)
		return
	}
	request := &NotifyLearnBeforeIndexerWriteRequest{
		OperationType: operationType,
		Object: string(jsonObject),
	}
	var response Response
	err = client.Call("LearnListener.NotifyBeforeIndexerWrite", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyLearnBeforeIndexerWrite")
	client.Close()
}

// func NotifyLearnBeforeQAdd() {
// 	if !checkMode(learn) {
// 		return
// 	}
// 	log.Printf("[sonar][NotifyLearnBeforeQAdd]\n")
// 	client, err := newClient()
// 	if err != nil {
// 		printError(err, connectionError)
// 		return
// 	}
// 	request := &NotifyLearnBeforeQAddRequest{
// 		Nothing: "nothing",
// 	}
// 	var response Response
// 	err = client.Call("LearnListener.NotifyBeforeQAdd", request, &response)
// 	if err != nil {
// 		printError(err, replyError)
// 		return
// 	}
// 	checkResponse(response, "NotifyLearnBeforeQAdd")
// 	client.Close()
// }

func NotifyLearnBeforeReconcile() {
	if !checkMode(learn) {
		return
	}
	log.Printf("[sonar][NotifyLearnBeforeReconcile]\n")
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	request := &NotifyLearnBeforeReconcileRequest{
		Nothing: "nothing",
	}
	var response Response
	err = client.Call("LearnListener.NotifyBeforeReconcile", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyLearnBeforeReconcile")
	client.Close()
}

func NotifyLearnAfterReconcile() {
	if !checkMode(learn) {
		return
	}
	log.Printf("[sonar][NotifyLearnAfterReconcile]\n")
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	request := &NotifyLearnAfterReconcileRequest{
		Nothing: "nothing",
	}
	var response Response
	err = client.Call("LearnListener.NotifyAfterReconcile", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyLearnAfterReconcile")
	client.Close()
}

func NotifyLearnSideEffects(sideEffectType string) {
	if !checkMode(learn) {
		return
	}
	log.Printf("[sonar][NotifyLearnSideEffects]\n")
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	request := &NotifyLearnSideEffectsRequest{
		SideEffectType: sideEffectType,
	}
	var response Response
	err = client.Call("LearnListener.NotifySideEffects", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyLearnSideEffects")
	client.Close()
}
