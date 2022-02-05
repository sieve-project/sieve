package sieve

import (
	"encoding/json"
	"log"
	"strings"

	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/types"
)

func NotifyUnobsrStateBeforeIndexerWrite(operationType string, object interface{}) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(TEST) || !checkMode(UNOBSERVED_STATE) {
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
	log.Printf("[sieve][NotifyUnobsrStateBeforeIndexerWrite] type: %s object: %s\n", operationType, string(jsonObject))
	request := &NotifyUnobsrStateBeforeIndexerWriteRequest{
		OperationType: operationType,
		Object:        string(jsonObject),
		ResourceType:  rType,
	}
	var response Response
	err = client.Call("UnobsrStateListener.NotifyUnobsrStateBeforeIndexerWrite", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyUnobsrStateBeforeIndexerWrite")
	client.Close()
}

func NotifyUnobsrStateAfterIndexerWrite(operationType string, object interface{}) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(TEST) || !checkMode(UNOBSERVED_STATE) {
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
	log.Printf("[sieve][NotifyUnobsrStateAfterIndexerWrite] type: %s object: %s\n", operationType, string(jsonObject))
	request := &NotifyUnobsrStateAfterIndexerWriteRequest{
		OperationType: operationType,
		Object:        string(jsonObject),
		ResourceType:  rType,
	}
	var response Response
	err = client.Call("UnobsrStateListener.NotifyUnobsrStateAfterIndexerWrite", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyUnobsrStateAfterIndexerWrite")
	client.Close()
}

func NotifyUnobsrStateBeforeInformerCacheGet(readType string, namespacedName types.NamespacedName, object interface{}) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(TEST) || !checkMode(UNOBSERVED_STATE) {
		return
	}
	rType := regularizeType(object)
	if rType != config["ce-rtype"].(string) {
		return
	}
	if namespacedName.Name != config["ce-name"].(string) || namespacedName.Namespace != config["ce-namespace"].(string) {
		return
	}
	log.Printf("[sieve][NotifyUnobsrStateBeforeInformerCacheGet] type: %s, ns: %s name: %s", rType, namespacedName.Namespace, namespacedName.Name)
	client, err := newClient()
	if err != nil {
		printError(err, SIEVE_CONN_ERR)
		return
	}
	request := &NotifyUnobsrStateBeforeInformerCacheReadRequest{
		OperationType: readType,
		ResourceType:  rType,
		Namespace:     namespacedName.Namespace,
		Name:          namespacedName.Name,
	}
	var response Response
	err = client.Call("UnobsrStateListener.NotifyUnobsrStateBeforeInformerCacheRead", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyUnobsrStateBeforeInformerCacheGet")
	client.Close()
}

func NotifyUnobsrStateAfterInformerCacheGet(readType string, namespacedName types.NamespacedName, object interface{}) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(TEST) || !checkMode(UNOBSERVED_STATE) {
		return
	}
	rType := regularizeType(object)
	if rType != config["ce-rtype"].(string) {
		return
	}
	if namespacedName.Name != config["ce-name"].(string) || namespacedName.Namespace != config["ce-namespace"].(string) {
		return
	}
	log.Printf("[sieve][NotifyUnobsrStateAfterInformerCacheGet] type: %s, ns: %s name: %s", rType, namespacedName.Namespace, namespacedName.Name)
	client, err := newClient()
	if err != nil {
		printError(err, SIEVE_CONN_ERR)
		return
	}
	request := &NotifyUnobsrStateAfterInformerCacheReadRequest{
		OperationType: readType,
		ResourceType:  rType,
		Namespace:     namespacedName.Namespace,
		Name:          namespacedName.Name,
	}
	var response Response
	err = client.Call("UnobsrStateListener.NotifyUnobsrStateAfterInformerCacheRead", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyUnobsrStateAfterInformerCacheGet")
	client.Close()
}

func NotifyUnobsrStateBeforeInformerCacheList(readType string, object interface{}) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(TEST) || !checkMode(UNOBSERVED_STATE) {
		return
	}
	rType := regularizeType(object)
	if rType != config["ce-rtype"].(string)+"list" {
		return
	}
	log.Printf("[sieve][NotifyUnobsrStateBeforeInformerCacheList] type: %s", rType)
	client, err := newClient()
	if err != nil {
		printError(err, SIEVE_CONN_ERR)
		return
	}
	request := &NotifyUnobsrStateBeforeInformerCacheReadRequest{
		OperationType: readType,
		ResourceType:  rType,
	}
	var response Response
	err = client.Call("UnobsrStateListener.NotifyUnobsrStateBeforeInformerCacheRead", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyUnobsrStateBeforeInformerCacheList")
	client.Close()
}

func NotifyUnobsrStateAfterInformerCacheList(readType string, object interface{}) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(TEST) || !checkMode(UNOBSERVED_STATE) {
		return
	}
	rType := regularizeType(object)
	if rType != config["ce-rtype"].(string)+"list" {
		return
	}
	log.Printf("[sieve][NotifyUnobsrStateAfterInformerCacheList] type: %s", rType)
	client, err := newClient()
	if err != nil {
		printError(err, SIEVE_CONN_ERR)
		return
	}
	request := &NotifyUnobsrStateAfterInformerCacheReadRequest{
		OperationType: readType,
		ResourceType:  rType,
	}
	var response Response
	err = client.Call("UnobsrStateListener.NotifyUnobsrStateAfterInformerCacheRead", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyUnobsrStateAfterInformerCacheList")
	client.Close()
}

func NotifyUnobsrStateAfterSideEffects(sideEffectID int, sideEffectType string, object interface{}, k8sErr error) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(TEST) || !checkMode(UNOBSERVED_STATE) {
		return
	}
	log.Printf("[sieve][NotifyUnobsrStateAfterSideEffects] %s %v\n", sideEffectType, object)
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
	request := &NotifyUnobsrStateAfterSideEffectsRequest{
		SideEffectID:   sideEffectID,
		SideEffectType: sideEffectType,
		Object:         string(jsonObject),
		ResourceType:   regularizeType(object),
		Error:          errorString,
	}
	var response Response
	err = client.Call("UnobsrStateListener.NotifyUnobsrStateAfterSideEffects", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyUnobsrStateAfterSideEffects")
	client.Close()
}

func NotifyUnobsrStateBeforeProcessEvent(eventType, key string, object interface{}) {
	loadSieveConfigMap(eventType, key, object)
	if err := loadSieveConfig(); err != nil {
		return
	}
	tokens := strings.Split(key, "/")
	namespace := tokens[len(tokens)-2]
	if namespace == config["ce-namespace"].(string) {
		if !checkStage(TEST) || !checkMode(UNOBSERVED_STATE) {
			return
		}
		jsonObject, err := json.Marshal(object)
		if err != nil {
			printError(err, SIEVE_JSON_ERR)
			return
		}
		if len(tokens) < 4 {
			log.Printf("unrecognizable key %s\n", key)
			return
		}
		resourceType := regularizeType(object)
		namespace := tokens[len(tokens)-2]
		name := tokens[len(tokens)-1]
		log.Printf("[SIEVE-API-EVENT]\t%s\t%s\t%s\t%s\t%s\t%s\n", eventType, key, resourceType, namespace, name, string(jsonObject))
	}
}
