package sieve

import (
	"encoding/json"

	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/types"
)

func NotifyAtomVioAfterOperatorGet(readType string, namespacedName types.NamespacedName, object interface{}, k8sErr error) {
	if !checkStage(TEST) || !checkMode(ATOM_VIO) {
		return
	}
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
	request := &NotifyAtomVioAfterOperatorGetRequest{
		ResourceType: regularizeType(object),
		Namespace:    namespacedName.Namespace,
		Name:         namespacedName.Name,
		Object:       string(jsonObject),
		Error:        errorString,
	}
	var response Response
	err = client.Call("AtomVioListener.NotifyAtomVioAfterOperatorGet", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyAtomVioAfterOperatorGet")
	client.Close()
}

func NotifyAtomVioAfterOperatorList(readType string, object interface{}, k8sErr error) {
	if !checkStage(TEST) || !checkMode(ATOM_VIO) {
		return
	}
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
	request := &NotifyAtomVioAfterOperatorListRequest{
		ResourceType: regularizeType(object),
		ObjectList:   string(jsonObject),
		Error:        errorString,
	}
	var response Response
	err = client.Call("AtomVioListener.NotifyAtomVioAfterOperatorList", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyAtomVioAfterOperatorList")
	client.Close()
}

func NotifyAtomVioAfterSideEffects(sideEffectID int, sideEffectType string, object interface{}, k8sErr error) {
	if !checkStage(TEST) || !checkMode(ATOM_VIO) {
		return
	}
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
	request := &NotifyAtomVioAfterSideEffectsRequest{
		SideEffectID:   sideEffectID,
		SideEffectType: sideEffectType,
		Object:         string(jsonObject),
		ResourceType:   regularizeType(object),
		Error:          errorString,
	}
	var response Response
	err = client.Call("AtomVioListener.NotifyAtomVioAfterSideEffects", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyAtomVioAfterSideEffects")
	client.Close()
}
