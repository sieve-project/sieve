package sieve

import (
	"encoding/json"
	"log"

	"k8s.io/apimachinery/pkg/api/errors"
)

func NotifyObsGapBeforeIndexerWrite(operationType string, object interface{}) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(TEST) || !checkMode(OBS_GAP) {
		return
	}
	rType := regularizeType(object)
	if rType != config["ce-rtype"].(string) {
		return
	}
	if !isSameObjectClientSide(object, config["ce-namespace"].(string), config["ce-name"].(string)) {
		return
	}
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
	log.Printf("[sieve][NotifyObsGapBeforeIndexerWrite] type: %s object: %s\n", operationType, string(jsonObject))
	request := &NotifyObsGapBeforeIndexerWriteRequest{
		OperationType: operationType,
		Object:        string(jsonObject),
		ResourceType:  rType,
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
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(TEST) || !checkMode(OBS_GAP) {
		return
	}
	rType := regularizeType(object)
	if rType != config["ce-rtype"].(string) {
		return
	}
	if !isSameObjectClientSide(object, config["ce-namespace"].(string), config["ce-name"].(string)) {
		return
	}
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
	log.Printf("[sieve][NotifyObsGapAfterIndexerWrite] type: %s object: %s\n", operationType, string(jsonObject))
	request := &NotifyObsGapAfterIndexerWriteRequest{
		OperationType: operationType,
		Object:        string(jsonObject),
		ResourceType:  rType,
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
	if err := loadSieveConfig(); err != nil {
		return
	}
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
	if err := loadSieveConfig(); err != nil {
		return
	}
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
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(TEST) || !checkMode(OBS_GAP) {
		return
	}
	log.Printf("[sieve][NotifyObsGapAfterSideEffects] %s %v\n", sideEffectType, object)
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return
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
