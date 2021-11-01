package sieve

import (
	"encoding/json"
	"log"
	"strings"

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
	rType := regularizeType(object)
	if !(config["se-etype-previous"].(string) == "Get" && rType == config["se-rtype"].(string)) {
		return
	}
	if !isSameObjectClientSide(object, config["se-namespace"].(string), config["se-name"].(string)) {
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
	rType := regularizeType(object)
	if !(config["se-etype-previous"].(string) == "List" && rType == config["se-rtype"].(string)+"list") {
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
	errorString := "NoError"
	if k8sErr != nil {
		errorString = string(errors.ReasonForError(k8sErr))
	}
	rType := regularizeType(object)
	if !(rType == config["se-rtype"].(string) && errorString == "NoError") {
		return
	}
	if !isSameObjectClientSide(object, config["se-namespace"].(string), config["se-name"].(string)) {
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
	request := &NotifyAtomVioAfterSideEffectsRequest{
		SideEffectID:   sideEffectID,
		SideEffectType: sideEffectType,
		Object:         string(jsonObject),
		ResourceType:   rType,
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

func NotifyAtomVioBeforeProcessEvent(eventType, key string, object interface{}) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	tokens := strings.Split(key, "/")
	namespace := tokens[len(tokens)-2]
	if namespace == config["se-namespace"].(string) {
		if !checkStage(TEST) || !checkMode(ATOM_VIO) {
			return
		}
		jsonObject, err := json.Marshal(object)
		if err != nil {
			printError(err, SIEVE_JSON_ERR)
			return
		}
		log.Printf("[SIEVE-API-EVENT]\t%s\t%s\t%s\n", eventType, key, string(jsonObject))
	}
}
