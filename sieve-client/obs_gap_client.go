package sieve

import (
	"encoding/json"
	"log"

	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/types"
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

func NotifyObsGapBeforeInformerCacheGet(readType string, namespacedName types.NamespacedName, object interface{}) {
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
	if namespacedName.Name != config["ce-name"].(string) || namespacedName.Namespace != config["ce-namespace"].(string) {
		return
	}
	log.Printf("[sieve][NotifyObsGapBeforeInformerCacheGet] type: %s, ns: %s name: %s", rType, namespacedName.Namespace, namespacedName.Name)
	client, err := newClient()
	if err != nil {
		printError(err, SIEVE_CONN_ERR)
		return
	}
	request := &NotifyObsGapBeforeInformerCacheReadRequest{
		OperationType: readType,
		ResourceType:  rType,
		Namespace:     namespacedName.Namespace,
		Name:          namespacedName.Name,
	}
	var response Response
	err = client.Call("ObsGapListener.NotifyObsGapBeforeInformerCacheRead", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyObsGapBeforeInformerCacheGet")
	client.Close()
}

func NotifyObsGapAfterInformerCacheGet(readType string, namespacedName types.NamespacedName, object interface{}) {
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
	if namespacedName.Name != config["ce-name"].(string) || namespacedName.Namespace != config["ce-namespace"].(string) {
		return
	}
	log.Printf("[sieve][NotifyObsGapAfterInformerCacheGet] type: %s, ns: %s name: %s", rType, namespacedName.Namespace, namespacedName.Name)
	client, err := newClient()
	if err != nil {
		printError(err, SIEVE_CONN_ERR)
		return
	}
	request := &NotifyObsGapAfterInformerCacheReadRequest{
		OperationType: readType,
		ResourceType:  rType,
		Namespace:     namespacedName.Namespace,
		Name:          namespacedName.Name,
	}
	var response Response
	err = client.Call("ObsGapListener.NotifyObsGapAfterInformerCacheRead", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyObsGapAfterInformerCacheGet")
	client.Close()
}

func NotifyObsGapBeforeInformerCacheList(readType string, object interface{}) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(TEST) || !checkMode(OBS_GAP) {
		return
	}
	rType := regularizeType(object)
	if rType != config["ce-rtype"].(string)+"list" {
		return
	}
	log.Printf("[sieve][NotifyObsGapBeforeInformerCacheList] type: %s", rType)
	client, err := newClient()
	if err != nil {
		printError(err, SIEVE_CONN_ERR)
		return
	}
	request := &NotifyObsGapBeforeInformerCacheReadRequest{
		OperationType: readType,
		ResourceType:  rType,
	}
	var response Response
	err = client.Call("ObsGapListener.NotifyObsGapBeforeInformerCacheRead", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyObsGapBeforeInformerCacheList")
	client.Close()
}

func NotifyObsGapAfterInformerCacheList(readType string, object interface{}) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(TEST) || !checkMode(OBS_GAP) {
		return
	}
	rType := regularizeType(object)
	if rType != config["ce-rtype"].(string)+"list" {
		return
	}
	log.Printf("[sieve][NotifyObsGapAfterInformerCacheList] type: %s", rType)
	client, err := newClient()
	if err != nil {
		printError(err, SIEVE_CONN_ERR)
		return
	}
	request := &NotifyObsGapAfterInformerCacheReadRequest{
		OperationType: readType,
		ResourceType:  rType,
	}
	var response Response
	err = client.Call("ObsGapListener.NotifyObsGapAfterInformerCacheRead", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyObsGapAfterInformerCacheList")
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

func NotifyObsGapBeforeProcessEvent(eventType, key string, object interface{}) {
	if eventType == "ADDED" || eventType == "DELETED" {
		if err := loadSieveConfig(); err != nil {
			return
		}
		if !checkStage(TEST) || !checkMode(OBS_GAP) {
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
