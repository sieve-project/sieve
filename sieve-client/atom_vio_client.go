package sieve

import (
	"encoding/json"
	"log"
	"reflect"
	"runtime/debug"
)

func NotifyAtomVioBeforeIndexerWrite(operationType string, object interface{}) {
	if !checkStage(TEST) || !checkMode(ATOM_VIO) {
		return
	}
	log.Printf("[sieve][NotifyAtomVioBeforeIndexerWrite] operationType: %s\n", operationType)
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

	request := &NotifyAtomVioBeforeIndexerWriteRequest{
		OperationType: operationType,
		Object:        string(jsonObject),
		ResourceType:  regularizeType(reflect.TypeOf(object).String()),
	}
	var response Response
	err = client.Call("AtomVioListener.NotifyAtomVioBeforeIndexerWrite", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyAtomVioBeforeIndexerWrite")
	client.Close()
}

func NotifyAtomVioBeforeSideEffects(sideEffectType string, object interface{}) {
	if !checkStage(TEST) || !checkMode(ATOM_VIO) {
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
	request := &NotifyAtomVioSideEffectsRequest{
		SideEffectType: sideEffectType,
		Object:         string(jsonObject),
		ResourceType:   regularizeType(reflect.TypeOf(object).String()),
		Error:          errorString,
		Stack:          string(debug.Stack()),
	}
	var response Response
	err = client.Call("AtomVioListener.NotifyAtomVioSideEffects", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyAtomVioSideEffects")
	client.Close()
}

func NotifyAtomVioAfterSideEffects(sideEffectType string, object interface{}, k8sErr error) {

}
