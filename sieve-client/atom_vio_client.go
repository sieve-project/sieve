package sieve

import (
	"encoding/json"
	"log"
	"reflect"

	"k8s.io/apimachinery/pkg/api/errors"
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
	request := &NotifyAtomVioBeforeSideEffectsRequest{
		SideEffectType: sideEffectType,
		Object:         string(jsonObject),
		ResourceType:   regularizeType(reflect.TypeOf(object).String()),
	}
	var response Response
	err = client.Call("AtomVioListener.NotifyAtomVioBeforeSideEffects", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyAtomVioBeforeSideEffects")
	client.Close()
}

func NotifyAtomVioAfterSideEffects(sideEffectType string, object interface{}, k8sErr error) {
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
	if k8sErr != nil {
		errorString = string(errors.ReasonForError(k8sErr))
	}
	request := &NotifyAtomVioAfterSideEffectsRequest{
		SideEffectType: sideEffectType,
		Object:         string(jsonObject),
		ResourceType:   regularizeType(reflect.TypeOf(object).String()),
		Error:          errorString,
	}
	var response Response
	err = client.Call("AtomVioListener.NotifyAtomVioAfterSideEffects", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyAtomVioAfterSideEffects")
	client.Close()
}
