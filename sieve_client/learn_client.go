package sieve

import (
	"encoding/json"
	"log"
	"strings"

	"k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/meta"
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

func NotifyLearnBeforeReconcile(stackFrame string) {
	if err := loadSieveConfigFromEnv(false); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	log.Printf("NotifyLearnBeforeReconcile %s", stackFrame)
	request := &NotifyLearnBeforeReconcileRequest{
		ReconcilerName: stackFrame,
	}
	var response Response
	err := rpcClient.Call("LearnListener.NotifyLearnBeforeReconcile", request, &response)
	if err != nil {
		printRPCError(err)
		return
	}
	checkResponse(response)
}

func NotifyLearnAfterReconcile(stackFrame string) {
	if err := loadSieveConfigFromEnv(false); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	log.Printf("NotifyLearnAfterReconcile %s", stackFrame)
	request := &NotifyLearnAfterReconcileRequest{
		ReconcilerName: stackFrame,
	}
	var response Response
	err := rpcClient.Call("LearnListener.NotifyLearnAfterReconcile", request, &response)
	if err != nil {
		printRPCError(err)
		return
	}
	checkResponse(response)
}

func NotifyLearnBeforeCacheGet(key string, items []interface{}) {
}

func NotifyLearnAfterCacheGet(key string, item interface{}, exists bool) {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	reconcileFun := getMatchedReconcileStackFrame()
	if reconcileFun == UNKNOWN_RECONCILE_FUN {
		return
	}
	serializedObj, err := json.Marshal(item)
	if err != nil {
		printSerializationError(err)
		return
	}
	if !exists {
		return
	}
	resourceType := getResourceTypeFromObj(item)
	tokens := strings.Split(key, "/")
	if len(tokens) != 2 {
		return
	}
	namespace := tokens[0]
	name := tokens[1]
	log.Printf("NotifyLearnAfterCacheGet %s %s %s %s", resourceType, namespace, name, string(serializedObj))
	request := &NotifyLearnAfterCacheGetRequest{
		ResourceType: resourceType,
		Namespace:    namespace,
		Name:         name,
		Object:       string(serializedObj),
		ReconcileFun: reconcileFun,
		Error:        NO_ERROR,
	}
	var response Response
	err = rpcClient.Call("LearnListener.NotifyLearnAfterCacheGet", request, &response)
	if err != nil {
		printRPCError(err)
		return
	}
	checkResponse(response)
}

func NotifyLearnBeforeCacheList(items []interface{}) {
}

func NotifyLearnAfterCacheList(items []interface{}, listErr error) {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	reconcileFun := getMatchedReconcileStackFrame()
	if reconcileFun == UNKNOWN_RECONCILE_FUN {
		return
	}
	serializedObjList, err := json.Marshal(items)
	if err != nil {
		printSerializationError(err)
		return
	}
	if listErr != nil {
		return
	}
	if len(items) == 0 {
		return
	}
	resourceType := getResourceTypeFromObj(items[0])
	log.Printf("NotifyLearnAfterCacheList %s %s", resourceType, string(serializedObjList))
	request := &NotifyLearnAfterCacheListRequest{
		ResourceType: resourceType,
		ObjectList:   string(serializedObjList),
		ReconcileFun: reconcileFun,
		Error:        NO_ERROR,
	}
	var response Response
	err = rpcClient.Call("LearnListener.NotifyLearnAfterCacheList", request, &response)
	if err != nil {
		printRPCError(err)
		return
	}
	checkResponse(response)
}

func NotifyLearnBeforeRestCall(verb string, pathPrefix string, subpath string, namespace string, namespaceSet bool, resourceType string, resourceName string, subresource string, object interface{}) int {
	log.Printf("NotifyLearnBeforeRestCall")
	if err := loadSieveConfigFromEnv(false); err != nil {
		return -1
	}
	if err := initRPCClient(); err != nil {
		return -1
	}
	reconcileFun := getMatchedReconcileStackFrame()
	if reconcileFun == UNKNOWN_RECONCILE_FUN {
		return -1
	}
	controllerOperationType := HttpVerbToControllerOperation(verb, resourceName, subresource)
	if controllerOperationType == UNKNOWN {
		log.Println("Unknown operation")
		return -1
	} else if controllerOperationType == GET || controllerOperationType == LIST {
		log.Println("Read operation")
		request := &NotifyLearnBeforeRestReadRequest{}
		var response Response
		err := rpcClient.Call("LearnListener.NotifyLearnBeforeRestRead", request, &response)
		if err != nil {
			printRPCError(err)
			return -1
		}
		checkResponse(response)
		return response.Number
	} else {
		log.Println("Write operation")
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
	log.Printf("NotifyLearnAfterRestCall")

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
	reconcileFun := getMatchedReconcileStackFrame()
	if reconcileFun == UNKNOWN_RECONCILE_FUN {
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
		log.Println("READ operation")
		request := &NotifyLearnAfterRestReadRequest{
			ControllerOperationID:   controllerOperationID,
			ControllerOperationType: controllerOperationType,
			ReconcileFun:            reconcileFun,
			ResourceType:            pluralToSingular(resourceType),
			Namespace:               namespace,
			Name:                    resourceName,
			ObjectBody:              string(serializedObj),
			Error:                   errorString,
		}
		var response Response
		err = rpcClient.Call("LearnListener.NotifyLearnAfterRestRead", request, &response)
		if err != nil {
			printRPCError(err)
			return
		}
		checkResponse(response)
	} else {
		log.Println("Write operation")
		request := &NotifyLearnAfterRestWriteRequest{
			ControllerOperationID:   controllerOperationID,
			ControllerOperationType: controllerOperationType,
			ReconcileFun:            reconcileFun,
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
	reconcileFun := getMatchedReconcileStackFrame()
	request := &NotifyLearnBeforeAnnotatedAPICallRequest{
		ModuleName:   moduleName,
		FilePath:     filePath,
		ReceiverType: receiverType,
		FunName:      funName,
		ReconcileFun: reconcileFun,
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
	reconcileFun := getMatchedReconcileStackFrame()
	request := &NotifyLearnAfterAnnotatedAPICallRequest{
		InvocationID: invocationID,
		ModuleName:   moduleName,
		FilePath:     filePath,
		ReceiverType: receiverType,
		FunName:      funName,
		ReconcileFun: reconcileFun,
	}
	var response Response
	err := rpcClient.Call("LearnListener.NotifyLearnAfterAnnotatedAPICall", request, &response)
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
