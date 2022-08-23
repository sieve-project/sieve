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

func HttpVerbToControllerOperation(verb, subresource string) string {
	switch verb {
	case "POST":
		return "Create"
	case "PUT":
		if subresource == "status" {
			return "StatusUpdate"
		} else {
			return "Update"
		}
	case "DELETE":
		return "Delete"
	default:
		return "Unknown"
	}
}

func NotifyLearnBeforeRestCall(verb string, subresource string) int {
	if err := loadSieveConfigFromEnv(false); err != nil {
		return -1
	}
	if err := initRPCClient(); err != nil {
		return -1
	}
	reconcilerType := getReconcilerFromStackTrace()
	if reconcilerType == "unknown" {
		return -1
	}
	controllerOperation := HttpVerbToControllerOperation(verb, subresource)
	if controllerOperation == "Unknown" {
		log.Println("Unknown operation")
		return 1
	} else if controllerOperation == "Get" || controllerOperation == "List" {
		log.Println("Get and List not supported yet")
		return 1
	} else {
		request := &NotifyLearnBeforeRestWriteRequest{
			SideEffectType: controllerOperation,
		}
		var response Response
		err := rpcClient.Call("LearnListener.NotifyLearnBeforeRestWrite", request, &response)
		if err != nil {
			printError(err, SIEVE_REPLY_ERR)
			return -1
		}
		checkResponse(response, "NotifyLearnBeforeRestWrite")
		return response.Number
	}
}

func NotifyLearnAfterRestCall(sideEffectID int, verb string, pathPrefix string, subpath string, namespace string, namespaceSet bool, resource string, resourceName string, subresource string, obj interface{}, serializationErr error, respErr error) {
	if err := loadSieveConfigFromEnv(false); err != nil {
		return
	}
	if sideEffectID == -1 {
		return
	}
	if serializationErr != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	reconcilerType := getReconcilerFromStackTrace()
	if reconcilerType == "unknown" {
		return
	}
	serializedObj, err := json.Marshal(obj)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return
	}
	errorString := "NoError"
	if respErr != nil {
		errorString = string(errors.ReasonForError(respErr))
	}
	controllerOperation := HttpVerbToControllerOperation(verb, subresource)
	if controllerOperation == "Unknown" {
		log.Println("Unknown operation")
	} else if controllerOperation == "Get" || controllerOperation == "List" {
		log.Println("Get and List not supported yet")
	} else {
		request := &NotifyLearnAfterRestWriteRequest{
			SideEffectID:   sideEffectID,
			SideEffectType: controllerOperation,
			ReconcilerType: reconcilerType,
			ResourceType:   resource,
			Namespace:      namespace,
			Name:           resourceName,
			ObjectBody:     string(serializedObj),
			Error:          errorString,
		}
		var response Response
		err = rpcClient.Call("LearnListener.NotifyLearnAfterRestWrite", request, &response)
		if err != nil {
			printError(err, SIEVE_REPLY_ERR)
			return
		}
		checkResponse(response, "NotifyLearnAfterRestWrite")
	}
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
