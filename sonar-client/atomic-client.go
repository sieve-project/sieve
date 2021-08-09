package sonar

import (
	"encoding/json"
	"log"
	"reflect"
	"runtime/debug"
)

func NotifyAtomicBeforeIndexerWrite(operationType string, object interface{}) {
	if !checkStage(test) || !checkMode(modeAtomic) {
		return
	}
	log.Printf("[sonar][NotifyAtomicBeforeIndexerWrite] operationType: %s\n", operationType)
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

	// if name == config["ce-name"].(string) && namespace == config["ce-namespace"].(string) && resourceType == config["ce-rtype"].(string) {
	// }
	request := &NotifyAtomicBeforeIndexerWriteRequest{
		OperationType: operationType,
		Object:        string(jsonObject),
		ResourceType:  regularizeType(reflect.TypeOf(object).String()),
	}
	var response Response
	err = client.Call("AtomicListener.NotifyAtomicBeforeIndexerWrite", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyAtomicBeforeIndexerWrite")
	client.Close()
}

func NotifyAtomicSideEffects(sideEffectType string, object interface{}) {
	if !checkStage(test) || !checkMode(modeAtomic) {
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, jsonError)
	}
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	errorString := "NoError"
	request := &NotifyAtomicSideEffectsRequest{
		SideEffectType: sideEffectType,
		Object:         string(jsonObject),
		ResourceType:   regularizeType(reflect.TypeOf(object).String()),
		Error:          errorString,
		Stack:          string(debug.Stack()),
	}
	var response Response
	err = client.Call("AtomicListener.NotifyAtomicSideEffects", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyAtomicSideEffects")
	client.Close()
}
