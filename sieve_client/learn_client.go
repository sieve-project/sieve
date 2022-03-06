package sieve

import (
	"encoding/json"
	"fmt"
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

func NotifyLearnBeforeControllerRecv(operationType string, object interface{}) int {
	if err := loadSieveConfigFromEnv(false); err != nil {
		return -1
	}
	if !triggerReconcile(object) {
		return -1
	}
	if err := initRPCClient(); err != nil {
		return -1
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return -1
	}
	request := &NotifyLearnBeforeControllerRecvRequest{
		OperationType: operationType,
		Object:        string(jsonObject),
		ResourceType:  regularizeType(object),
	}
	var response Response
	err = rpcClient.Call("LearnListener.NotifyLearnBeforeControllerRecv", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return -1
	}
	checkResponse(response, "NotifyLearnBeforeControllerRecv")
	return response.Number
}

func NotifyLearnAfterControllerRecv(recvID int, operationType string, object interface{}) {
	if err := loadSieveConfigFromEnv(false); err != nil {
		return
	}
	if !triggerReconcile(object) {
		return
	}
	if recvID == -1 {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	request := &NotifyLearnAfterControllerRecvRequest{
		EventID: recvID,
	}
	var response Response
	err := rpcClient.Call("LearnListener.NotifyLearnAfterControllerRecv", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyLearnAfterControllerRecv")
}

func NotifyLearnBeforeReconcile(reconciler interface{}) {
	if err := loadSieveConfigFromEnv(false); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	reconcilerName := fmt.Sprintf("%s.(*%s)", reflect.TypeOf(reconciler).Elem().PkgPath(), reflect.TypeOf(reconciler).Elem().Name())
	request := &NotifyLearnBeforeReconcileRequest{
		ReconcilerName: reconcilerName,
	}
	var response Response
	err := rpcClient.Call("LearnListener.NotifyLearnBeforeReconcile", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyLearnBeforeReconcile")
}

func NotifyLearnAfterReconcile(reconciler interface{}) {
	if err := loadSieveConfigFromEnv(false); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	reconcilerName := fmt.Sprintf("%s.(*%s)", reflect.TypeOf(reconciler).Elem().PkgPath(), reflect.TypeOf(reconciler).Elem().Name())
	request := &NotifyLearnBeforeReconcileRequest{
		ReconcilerName: reconcilerName,
	}
	var response Response
	err := rpcClient.Call("LearnListener.NotifyLearnAfterReconcile", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyLearnAfterReconcile")
}

func NotifyLearnBeforeControllerWrite(sideEffectType string, object interface{}) int {
	if err := loadSieveConfigFromEnv(false); err != nil {
		return -1
	}
	if err := initRPCClient(); err != nil {
		return -1
	}
	request := &NotifyLearnBeforeControllerWriteRequest{
		SideEffectType: sideEffectType,
	}
	var response Response
	err := rpcClient.Call("LearnListener.NotifyLearnBeforeControllerWrite", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return -1
	}
	checkResponse(response, "NotifyLearnBeforeControllerWrite")
	return response.Number
}

func NotifyLearnAfterControllerWrite(sideEffectID int, sideEffectType string, object interface{}, k8sErr error) {
	if err := loadSieveConfigFromEnv(false); err != nil {
		return
	}
	if sideEffectID == -1 {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	reconcilerType := getReconcilerFromStackTrace()
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return
	}
	errorString := "NoError"
	if k8sErr != nil {
		errorString = string(errors.ReasonForError(k8sErr))
	}
	request := &NotifyLearnAfterControllerWriteRequest{
		SideEffectID:   sideEffectID,
		SideEffectType: sideEffectType,
		Object:         string(jsonObject),
		ResourceType:   regularizeType(object),
		ReconcilerType: reconcilerType,
		Error:          errorString,
	}
	var response Response
	err = rpcClient.Call("LearnListener.NotifyLearnAfterControllerWrite", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyLearnAfterControllerWrite")
}

func NotifyLearnBeforeAnnotatedAPICall(moduleName string, filePath string, receiverType string, funName string) int {
	if err := loadSieveConfigFromEnv(false); err != nil {
		return -1
	}
	if err := initRPCClient(); err != nil {
		return -1
	}
	reconcilerType := getReconcilerFromStackTrace()
	request := &NotifyLearnBeforeAnnotatedAPICallRequest{
		ModuleName:     moduleName,
		FilePath:       filePath,
		ReceiverType:   receiverType,
		FunName:        funName,
		ReconcilerType: reconcilerType,
	}
	var response Response
	err := rpcClient.Call("LearnListener.NotifyLearnBeforeAnnotatedAPICall", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return -1
	}
	checkResponse(response, "NotifyLearnBeforeAnnotatedAPICall")
	return response.Number
}

func NotifyLearnAfterAnnotatedAPICall(invocationID int, moduleName string, filePath string, receiverType string, funName string) {
	if err := loadSieveConfigFromEnv(false); err != nil {
		return
	}
	if invocationID == -1 {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	reconcilerType := getReconcilerFromStackTrace()
	request := &NotifyLearnAfterAnnotatedAPICallRequest{
		InvocationID:   invocationID,
		ModuleName:     moduleName,
		FilePath:       filePath,
		ReceiverType:   receiverType,
		FunName:        funName,
		ReconcilerType: reconcilerType,
	}
	var response Response
	err := rpcClient.Call("LearnListener.NotifyLearnAfterAnnotatedAPICall", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyLearnAfterAnnotatedAPICall")
}

func NotifyLearnAfterControllerGet(readType string, fromCache bool, namespacedName types.NamespacedName, object interface{}, k8sErr error) {
	if err := loadSieveConfigFromEnv(false); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	reconcilerType := getReconcilerFromStackTrace()
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return
	}
	errorString := "NoError"
	if k8sErr != nil {
		errorString = string(errors.ReasonForError(k8sErr))
	}
	request := &NotifyLearnAfterControllerGetRequest{
		FromCache:      fromCache,
		ResourceType:   regularizeType(object),
		Namespace:      namespacedName.Namespace,
		Name:           namespacedName.Name,
		Object:         string(jsonObject),
		ReconcilerType: reconcilerType,
		Error:          errorString,
	}
	var response Response
	err = rpcClient.Call("LearnListener.NotifyLearnAfterControllerGet", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyLearnAfterControllerGet")
}

func NotifyLearnAfterControllerList(readType string, fromCache bool, object interface{}, k8sErr error) {
	if err := loadSieveConfigFromEnv(false); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	reconcilerType := getReconcilerFromStackTrace()
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return
	}
	errorString := "NoError"
	if k8sErr != nil {
		errorString = string(errors.ReasonForError(k8sErr))
	}
	request := &NotifyLearnAfterControllerListRequest{
		FromCache:      fromCache,
		ResourceType:   regularizeType(object),
		ObjectList:     string(jsonObject),
		ReconcilerType: reconcilerType,
		Error:          errorString,
	}
	var response Response
	err = rpcClient.Call("LearnListener.NotifyLearnAfterControllerList", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyLearnAfterControllerList")
}

func NotifyLearnBeforeAPIServerRecv(eventType, key string, object interface{}) {
	if err := loadSieveConfigFromConfigMap(eventType, key, object, false); err != nil {
		return
	}
	LogAPIEvent(eventType, key, object)
}
