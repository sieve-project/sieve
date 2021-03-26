package sonar

import (
	"fmt"
	"log"
	"reflect"
)

// NotifySparseReadBeforeMakeQ is invoked before controller creating a queue
// NotifySparseReadBeforeMakeQ lets the server know which controller creates which queue,
// this piece of information is not utilized by server so far.
func NotifySparseReadBeforeMakeQ(queue interface{}, controllerName string) {
	if !checkMode(sparseRead) {
		return
	}
	log.Printf("[sonar][NotifySparseReadBeforeMakeQ] queue: %p, controllerName: %s\n", queue, controllerName)
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	queueID := fmt.Sprintf("%p", queue)
	request := &NotifySparseReadBeforeMakeQRequest{
		QueueID:        queueID,
		ControllerName: controllerName,
	}
	var response Response
	err = client.Call("SparseReadListener.NotifySparseReadBeforeMakeQ", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifySparseReadBeforeMakeQ")
	client.Close()
}

// NotifySparseReadBeforeQAdd is invoked before controller calling q.Add
// NotifySparseReadBeforeQAdd lets the server know how busy the queues and controller are.
func NotifySparseReadBeforeQAdd(queue interface{}) {
	if !checkMode(sparseRead) {
		return
	}
	log.Printf("[sonar][NotifySparseReadBeforeQAdd] queue: %p\n", queue)
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	queueID := fmt.Sprintf("%p", queue)
	request := &NotifySparseReadBeforeQAddRequest{
		QueueID: queueID,
	}
	var response Response
	err = client.Call("SparseReadListener.NotifySparseReadBeforeQAdd", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifySparseReadBeforeQAdd")
	client.Close()
}

// NotifySparseReadBeforeReconcile is invoked before controller calling Reconcile()
// NotifySparseReadBeforeReconcile lets controller know a reconcile is going to happen,
// and the controller should decide whether to delay it.
func NotifySparseReadBeforeReconcile(controllerName string) {
	if !checkMode(sparseRead) {
		return
	}
	log.Printf("[sonar][NotifySparseReadBeforeReconcile] controllerName: %s\n", controllerName)
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	request := &NotifySparseReadBeforeReconcileRequest{
		ControllerName: controllerName,
	}
	var response Response
	err = client.Call("SparseReadListener.NotifySparseReadBeforeReconcile", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifySparseReadBeforeReconcile")
	client.Close()
}

func NotifySparseReadSideEffects(sideEffectType string, object interface{}) {
	if !checkMode(timeTravel) {
		return
	}
	log.Printf("[SONAR-SIDE-EFFECT]\t%s\t%s\n", sideEffectType, regularizeType(reflect.TypeOf(object).String()))
}
