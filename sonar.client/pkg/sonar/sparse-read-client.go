package sonar

import (
	"fmt"
	"log"
)

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