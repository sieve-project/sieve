package sieve

import (
	"encoding/json"
	"log"

	"k8s.io/apimachinery/pkg/api/errors"
)

func NotifyObsGapBeforeIndexerWrite(operationType string, object interface{}) {
	if !checkStage(TEST) || !checkMode(OBS_GAP) {
		return
	}

	log.Printf("[sieve][NotifyObsGapBeforeIndexerWrite] operationType: %s\n", operationType)
	client, err := newClient()
	if err != nil {
		printError(err, SIEVE_CONN_ERR)
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return
	}

	request := &NotifyObsGapBeforeIndexerWriteRequest{
		OperationType: operationType,
		Object:        string(jsonObject),
		ResourceType:  regularizeType(object),
	}
	var response Response
	err = client.Call("ObsGapListener.NotifyObsGapBeforeIndexerWrite", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
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
		printError(err, SIEVE_CONN_ERR)
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return
	}

	request := &NotifyObsGapAfterIndexerWriteRequest{
		OperationType: operationType,
		Object:        string(jsonObject),
		ResourceType:  regularizeType(object),
	}
	var response Response
	err = client.Call("ObsGapListener.NotifyObsGapAfterIndexerWrite", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
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
		printError(err, SIEVE_CONN_ERR)
		return
	}
	request := &NotifyObsGapBeforeReconcileRequest{
		ControllerName: controllerName,
	}
	var response Response
	err = client.Call("ObsGapListener.NotifyObsGapBeforeReconcile", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
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
		printError(err, SIEVE_CONN_ERR)
		return
	}
	request := &NotifyObsGapAfterReconcileRequest{
		ControllerName: controllerName,
	}
	var response Response
	err = client.Call("ObsGapListener.NotifyObsGapAfterReconcile", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyObsGapAfterReconcile")
	client.Close()
}

func NotifyObsGapAfterSideEffects(sideEffectID int, sideEffectType string, object interface{}, k8sErr error) {
	if !checkStage(TEST) || !checkMode(OBS_GAP) {
		return
	}
	// log.Printf("[sieve][NotifyTimeTravelSideEffects] %s %v\n", sideEffectType, object)
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
	}
	client, err := newClient()
	if err != nil {
		printError(err, SIEVE_CONN_ERR)
		return
	}
	errorString := "NoError"
	if k8sErr != nil {
		errorString = string(errors.ReasonForError(k8sErr))
	}
	request := &NotifyObsGapAfterSideEffectsRequest{
		SideEffectID:   sideEffectID,
		SideEffectType: sideEffectType,
		Object:         string(jsonObject),
		ResourceType:   regularizeType(object),
		Error:          errorString,
	}
	var response Response
	err = client.Call("ObsGapListener.NotifyObsGapAfterSideEffects", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyObsGapAfterSideEffects")
	client.Close()
}
