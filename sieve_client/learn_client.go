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
	rType := getResourceTypeFromObj(object)
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
		printSerializationError(err)
		return -1
	}
	request := &NotifyLearnBeforeControllerRecvRequest{
		OperationType: operationType,
		Object:        string(jsonObject),
		ResourceType:  getResourceTypeFromObj(object),
	}
	var response Response
	err = rpcClient.Call("LearnListener.NotifyLearnBeforeControllerRecv", request, &response)
	if err != nil {
		printRPCError(err)
		return -1
	}
	checkResponse(response)
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
		printRPCError(err)
		return
	}
	checkResponse(response)
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
		printRPCError(err)
		return
	}
	checkResponse(response)
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
		printRPCError(err)
		return
	}
	checkResponse(response)
}

func NotifyLearnBeforeRestCall(verb string, pathPrefix string, subpath string, namespace string, namespaceSet bool, resourceType string, resourceName string, subresource string, object interface{}) int {
	if err := loadSieveConfigFromEnv(false); err != nil {
		return -1
	}
	if err := initRPCClient(); err != nil {
		return -1
	}
	reconcilerType := getReconcilerFromStackTrace()
	if reconcilerType == UNKNOWN_RECONCILER_TYPE {
		return -1
	}
	controllerOperationType := HttpVerbToControllerOperation(verb, resourceName, subresource)
	if controllerOperationType == UNKNOWN {
		log.Println("Unknown operation")
		return -1
	} else if controllerOperationType == GET || controllerOperationType == LIST {
		log.Println("Get and List not supported yet")
		return -1
		// request := &NotifyLearnBeforeRestReadRequest{}
		// var response Response
		// err := rpcClient.Call("LearnListener.NotifyLearnBeforeRestRead", request, &response)
		// if err != nil {
		// 	printRPCError(err)
		// 	return -1
		// }
		// checkResponse(response)
		// return response.Number
	} else {
		request := &NotifyLearnBeforeRestWriteRequest{}
		var response Response
		err := rpcClient.Call("LearnListener.NotifyLearnBeforeRestWrite", request, &response)
		if err != nil {
			printRPCError(err)
			return -1
		}
		checkResponse(response)
		return response.Number
	}
}

func NotifyLearnAfterRestCall(controllerOperationID int, verb string, pathPrefix string, subpath string, namespace string, namespaceSet bool, resourceType string, resourceName string, subresource string, object interface{}, serializationErr error, respErr error) {
	if err := loadSieveConfigFromEnv(false); err != nil {
		return
	}
	if controllerOperationID == -1 {
		return
	}
	if serializationErr != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	reconcilerType := getReconcilerFromStackTrace()
	if reconcilerType == UNKNOWN_RECONCILER_TYPE {
		return
	}
	serializedObj, err := json.Marshal(object)
	if err != nil {
		printSerializationError(err)
		return
	}
	errorString := NO_ERROR
	if respErr != nil {
		errorString = string(errors.ReasonForError(respErr))
	}
	controllerOperationType := HttpVerbToControllerOperation(verb, resourceName, subresource)
	if controllerOperationType == UNKNOWN {
		log.Println("Unknown operation")
	} else if controllerOperationType == GET || controllerOperationType == LIST {
		log.Println("Get and List not supported yet")
	} else {
		request := &NotifyLearnAfterRestWriteRequest{
			ControllerOperationID:   controllerOperationID,
			ControllerOperationType: controllerOperationType,
			ReconcilerType:          reconcilerType,
			ResourceType:            pluralToSingular(resourceType),
			Namespace:               namespace,
			Name:                    resourceName,
			ObjectBody:              string(serializedObj),
			Error:                   errorString,
		}
		var response Response
		err = rpcClient.Call("LearnListener.NotifyLearnAfterRestWrite", request, &response)
		if err != nil {
			printRPCError(err)
			return
		}
		checkResponse(response)
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
		printRPCError(err)
		return -1
	}
	checkResponse(response)
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
		printRPCError(err)
		return
	}
	checkResponse(response)
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
		printSerializationError(err)
		return
	}
	errorString := NO_ERROR
	if k8sErr != nil {
		errorString = string(errors.ReasonForError(k8sErr))
	}
	request := &NotifyLearnAfterControllerGetRequest{
		FromCache:      fromCache,
		ResourceType:   getResourceTypeFromObj(object),
		Namespace:      namespacedName.Namespace,
		Name:           namespacedName.Name,
		Object:         string(jsonObject),
		ReconcilerType: reconcilerType,
		Error:          errorString,
	}
	var response Response
	err = rpcClient.Call("LearnListener.NotifyLearnAfterControllerGet", request, &response)
	if err != nil {
		printRPCError(err)
		return
	}
	checkResponse(response)
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
		printSerializationError(err)
		return
	}
	errorString := NO_ERROR
	if k8sErr != nil {
		errorString = string(errors.ReasonForError(k8sErr))
	}
	request := &NotifyLearnAfterControllerListRequest{
		FromCache:      fromCache,
		ResourceType:   getResourceTypeFromObj(object),
		ObjectList:     string(jsonObject),
		ReconcilerType: reconcilerType,
		Error:          errorString,
	}
	var response Response
	err = rpcClient.Call("LearnListener.NotifyLearnAfterControllerList", request, &response)
	if err != nil {
		printRPCError(err)
		return
	}
	checkResponse(response)
}

func NotifyLearnBeforeAPIServerRecv(eventType, key string, object interface{}) {
	if err := loadSieveConfigFromConfigMap(eventType, key, object, false); err != nil {
		return
	}
	LogAPIEvent(eventType, key, object)
}
