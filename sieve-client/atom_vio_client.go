package sieve

import (
	"encoding/json"

	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/types"
)

func NotifyAtomVioAfterOperatorGet(readType string, namespacedName types.NamespacedName, object interface{}, k8sErr error) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(TEST) || !checkMode(ATOM_VIO) {
		return
	}
	errorString := "NoError"
	if k8sErr != nil {
		errorString = string(errors.ReasonForError(k8sErr))
	}
	rType := regularizeType(object)
	if !(config["se-etype-previous"].(string) == "Get" && errorString == "NoError" && rType == config["se-rtype"].(string)) {
		return
	}
	if !isSameObjectClientSide(object, namespacedName.Namespace, namespacedName.Name) {
		return
	}
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
	defer client.Close()
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
}

func NotifyAtomVioAfterOperatorList(readType string, object interface{}, k8sErr error) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(TEST) || !checkMode(ATOM_VIO) {
		return
	}
	errorString := "NoError"
	if k8sErr != nil {
		errorString = string(errors.ReasonForError(k8sErr))
	}
	rType := regularizeType(object)
	if !(config["se-etype-previous"].(string) == "List" && errorString == "NoError" && rType == config["se-rtype"].(string)+"list") {
		return
	}
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
	defer client.Close()
	request := &NotifyAtomVioAfterOperatorListRequest{
		ResourceType: rType,
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
}

func NotifyAtomVioAfterSideEffects(sideEffectID int, sideEffectType string, object interface{}, k8sErr error) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(TEST) || !checkMode(ATOM_VIO) {
		return
	}
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
	defer client.Close()
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
}
