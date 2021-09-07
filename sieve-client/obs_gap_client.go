package sieve

import (
	"encoding/json"
	"log"
	"reflect"

	"k8s.io/apimachinery/pkg/api/errors"
)

func NotifyObsGapBeforeIndexerWrite(operationType string, object interface{}) {
	if !checkStage(TEST) || !checkMode(OBS_GAP) {
		return
	}
	// if !triggerReconcile(object) {
	// 	return -1
	// }
	log.Printf("[sieve][NotifyObsGapBeforeIndexerWrite] operationType: %s\n", operationType)
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
	request := &NotifyObsGapBeforeIndexerWriteRequest{
		OperationType: operationType,
		Object:        string(jsonObject),
		ResourceType:  regularizeType(reflect.TypeOf(object).String()),
	}
	var response Response
	err = client.Call("ObsGapListener.NotifyObsGapBeforeIndexerWrite", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyObsGapBeforeIndexerWrite")
	client.Close()
}

func NotifyObsGapAfterIndexerWrite(operationType string, object interface{}) {
	if !checkStage(TEST) || !checkMode(OBS_GAP) {
		return
	}
	log.Printf("[sieve][NotifyObsGapAfterIndexerWrite] operationType: %s\n", operationType)
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

	request := &NotifyObsGapAfterIndexerWriteRequest{
		OperationType: operationType,
		Object:        string(jsonObject),
		ResourceType:  regularizeType(reflect.TypeOf(object).String()),
	}
	var response Response
	err = client.Call("ObsGapListener.NotifyObsGapAfterIndexerWrite", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyObsGapAfterIndexerWrite")
	client.Close()
}

func NotifyObsGapBeforeReconcile(controllerName string) {
	if !checkStage(TEST) || !checkMode(OBS_GAP) {
		return
	}
	log.Printf("[sieve][NotifyObsGapBeforeReconcile]\n")
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	request := &NotifyObsGapBeforeReconcileRequest{
		ControllerName: controllerName,
	}
	var response Response
	err = client.Call("ObsGapListener.NotifyObsGapBeforeReconcile", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyObsGapBeforeReconcile")
	client.Close()
}

func NotifyObsGapAfterReconcile(controllerName string) {
	if !checkStage(TEST) || !checkMode(OBS_GAP) {
		return
	}
	log.Printf("[sieve][NotifyObsGapAfterReconcile]\n")
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	request := &NotifyObsGapAfterReconcileRequest{
		ControllerName: controllerName,
	}
	var response Response
	err = client.Call("ObsGapListener.NotifyObsGapAfterReconcile", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyObsGapAfterReconcile")
	client.Close()
}

func NotifyObsGapAfterSideEffects(sideEffectType string, object interface{}, k8sErr error) {
	if !checkStage(TEST) || !checkMode(OBS_GAP) {
		return
	}
	// log.Printf("[sieve][NotifyTimeTravelSideEffects] %s %v\n", sideEffectType, object)
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
	if k8sErr != nil {
		errorString = string(errors.ReasonForError(k8sErr))
	}
	request := &NotifyObsGapAfterSideEffectsRequest{
		SideEffectType: sideEffectType,
		Object:         string(jsonObject),
		ResourceType:   regularizeType(reflect.TypeOf(object).String()),
		Error:          errorString,
	}
	var response Response
	err = client.Call("ObsGapListener.NotifyObsGapAfterSideEffects", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyObsGapAfterSideEffects")
	client.Close()
}
