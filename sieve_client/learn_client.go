package sieve

import (
	"encoding/json"
	"fmt"
	"log"
	"reflect"
	"strings"

	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/meta"
	"k8s.io/apimachinery/pkg/types"
)

func isCRD(rType string, crds []string) bool {
	for _, crd := range crds {
		if rType == crd {
			return true
		}
	}
	return false
}

func triggerReconcile(object interface{}) bool {
	crds := getCRDs()
	rType := regularizeType(object)
	if isCRD(rType, crds) {
		return true
	}
	if o, err := meta.Accessor(object); err == nil {
		for _, ref := range o.GetOwnerReferences() {
			if isCRD(strings.ToLower(ref.Kind), crds) {
				taintMap.Store(o.GetNamespace()+"-"+rType+"-"+o.GetName(), "")
				return true
			} else if _, ok := taintMap.Load(o.GetNamespace() + "-" + strings.ToLower(ref.Kind) + "-" + ref.Name); ok {
				taintMap.Store(o.GetNamespace()+"-"+rType+"-"+o.GetName(), "")
				return true
			}
		}
	}
	return false
}

func NotifyLearnBeforeIndexerWrite(operationType string, object interface{}) int {
	if err := loadSieveConfig(); err != nil {
		return -1
	}
	if !checkStage(LEARN) {
		return -1
	}
	if !triggerReconcile(object) {
		return -1
	}
	// log.Printf("[sieve][NotifyLearnBeforeIndexerWrite] operationType: %s\n", operationType)
	client, err := newClient()
	if err != nil {
		printError(err, SIEVE_CONN_ERR)
		return -1
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return -1
	}
	request := &NotifyLearnBeforeIndexerWriteRequest{
		OperationType: operationType,
		Object:        string(jsonObject),
		ResourceType:  regularizeType(object),
	}
	var response Response
	err = client.Call("LearnListener.NotifyLearnBeforeIndexerWrite", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return -1
	}
	checkResponse(response, "NotifyLearnBeforeIndexerWrite")
	client.Close()
	return response.Number
}

func NotifyLearnAfterIndexerWrite(eventID int, object interface{}) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(LEARN) {
		return
	}
	if !triggerReconcile(object) {
		return
	}
	if eventID == -1 {
		return
	}
	// log.Printf("[sieve][NotifyLearnAfterIndexerWrite]\n")
	client, err := newClient()
	if err != nil {
		printError(err, SIEVE_CONN_ERR)
		return
	}
	request := &NotifyLearnAfterIndexerWriteRequest{
		EventID: eventID,
	}
	var response Response
	err = client.Call("LearnListener.NotifyLearnAfterIndexerWrite", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyLearnAfterIndexerWrite")
	client.Close()
}

func NotifyLearnBeforeReconcile(reconciler interface{}) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(LEARN) {
		return
	}
	// log.Printf("[sieve][NotifyLearnBeforeReconcile]\n")
	client, err := newClient()
	if err != nil {
		printError(err, SIEVE_CONN_ERR)
		return
	}
	reconcilerName := fmt.Sprintf("%s.(*%s)", reflect.TypeOf(reconciler).Elem().PkgPath(), reflect.TypeOf(reconciler).Elem().Name())
	request := &NotifyLearnBeforeReconcileRequest{
		ReconcilerName: reconcilerName,
	}
	var response Response
	err = client.Call("LearnListener.NotifyLearnBeforeReconcile", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyLearnBeforeReconcile")
	client.Close()
}

func NotifyLearnAfterReconcile(reconciler interface{}) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(LEARN) {
		return
	}
	// log.Printf("[sieve][NotifyLearnAfterReconcile]\n")
	client, err := newClient()
	if err != nil {
		printError(err, SIEVE_CONN_ERR)
		return
	}
	reconcilerName := fmt.Sprintf("%s.(*%s)", reflect.TypeOf(reconciler).Elem().PkgPath(), reflect.TypeOf(reconciler).Elem().Name())
	request := &NotifyLearnBeforeReconcileRequest{
		ReconcilerName: reconcilerName,
	}
	var response Response
	err = client.Call("LearnListener.NotifyLearnAfterReconcile", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyLearnAfterReconcile")
	client.Close()
}

func NotifyLearnBeforeSideEffects(sideEffectType string, object interface{}) int {
	if err := loadSieveConfig(); err != nil {
		return -1
	}
	if !checkStage(LEARN) {
		return -1
	}
	// log.Printf("[sieve][NotifyLearnBeforeSideEffects] %v\n", reflect.TypeOf(object))
	client, err := newClient()
	if err != nil {
		printError(err, SIEVE_CONN_ERR)
		return -1
	}
	request := &NotifyLearnBeforeSideEffectsRequest{
		SideEffectType: sideEffectType,
	}
	var response Response
	err = client.Call("LearnListener.NotifyLearnBeforeSideEffects", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return -1
	}
	checkResponse(response, "NotifyLearnBeforeSideEffects")
	client.Close()
	return response.Number
}

func NotifyLearnAfterSideEffects(sideEffectID int, sideEffectType string, object interface{}, k8sErr error) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(LEARN) {
		return
	}
	if sideEffectID == -1 {
		return
	}
	reconcilerType := getReconcilerFromStackTrace()
	if reconcilerType == "" {
		reconcilerType = UNKNOWN_RECONCILER_TYPE
	}
	// log.Printf("[sieve][NotifyLearnAfterSideEffects] %v\n", reflect.TypeOf(object))
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
	request := &NotifyLearnAfterSideEffectsRequest{
		SideEffectID:   sideEffectID,
		SideEffectType: sideEffectType,
		Object:         string(jsonObject),
		ResourceType:   regularizeType(object),
		ReconcilerType: reconcilerType,
		Error:          errorString,
	}
	var response Response
	err = client.Call("LearnListener.NotifyLearnAfterSideEffects", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyLearnAfterSideEffects")
	client.Close()
}

func NotifyLearnAfterOperatorGet(readType string, fromCache bool, namespacedName types.NamespacedName, object interface{}, k8sErr error) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(LEARN) {
		return
	}
	reconcilerType := getReconcilerFromStackTrace()
	if reconcilerType == "" {
		reconcilerType = UNKNOWN_RECONCILER_TYPE
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return
	}
	// log.Printf("[SIEVE] GET %s\n", string(jsonObject))
	client, err := newClient()
	if err != nil {
		printError(err, SIEVE_CONN_ERR)
		return
	}
	errorString := "NoError"
	if k8sErr != nil {
		errorString = string(errors.ReasonForError(k8sErr))
	}
	request := &NotifyLearnAfterOperatorGetRequest{
		FromCache:      fromCache,
		ResourceType:   regularizeType(object),
		Namespace:      namespacedName.Namespace,
		Name:           namespacedName.Name,
		Object:         string(jsonObject),
		ReconcilerType: reconcilerType,
		Error:          errorString,
	}
	var response Response
	err = client.Call("LearnListener.NotifyLearnAfterOperatorGet", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyLearnAfterOperatorGet")
	client.Close()
}

func NotifyLearnAfterOperatorList(readType string, fromCache bool, object interface{}, k8sErr error) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(LEARN) {
		return
	}
	reconcilerType := getReconcilerFromStackTrace()
	if reconcilerType == "" {
		reconcilerType = UNKNOWN_RECONCILER_TYPE
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return
	}
	// log.Printf("[SIEVE] LIST %s\n", string(jsonObject))
	client, err := newClient()
	if err != nil {
		printError(err, SIEVE_CONN_ERR)
		return
	}
	errorString := "NoError"
	if k8sErr != nil {
		errorString = string(errors.ReasonForError(k8sErr))
	}
	request := &NotifyLearnAfterOperatorListRequest{
		FromCache:      fromCache,
		ResourceType:   regularizeType(object),
		ObjectList:     string(jsonObject),
		ReconcilerType: reconcilerType,
		Error:          errorString,
	}
	var response Response
	err = client.Call("LearnListener.NotifyLearnAfterOperatorList", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyLearnAfterOperatorList")
	client.Close()
}

func NotifyLearnBeforeProcessEvent(eventType, key string, object interface{}) {
	loadSieveConfigMap(eventType, key, object)
	if err := loadSieveConfig(); err != nil {
		return
	}
	tokens := strings.Split(key, "/")
	namespace := tokens[len(tokens)-2]
	if namespace == config["namespace"].(string) {
		if !checkStage(LEARN) {
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
