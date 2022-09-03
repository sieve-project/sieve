package sieve

import (
	"encoding/json"
	"log"
	"path"
)

func NotifyTestBeforeControllerRecv(operationType string, object interface{}) int {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return -1
	}
	if err := initRPCClient(); err != nil {
		return -1
	}
	resourceType := getResourceTypeFromObj(object)
	name, namespace := extractNameNamespaceFromObj(object)
	resourceKey := generateResourceKey(resourceType, namespace, name)
	if !checkKVPairInTriggerObservationPoint(resourceKey, "when", "beforeControllerRecv", false) {
		return -1
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printSerializationError(err)
		return -1
	}
	log.Printf("NotifyTestBeforeControllerRecv %s %s %s\n", operationType, resourceKey, string(jsonObject))
	request := &NotifyTestBeforeControllerRecvRequest{
		OperationType: operationType,
		ResourceKey:   resourceKey,
		Object:        string(jsonObject),
	}
	var response Response
	err = rpcClient.Call("TestCoordinator.NotifyTestBeforeControllerRecv", request, &response)
	if err != nil {
		printRPCError(err)
		return -1
	}
	checkResponse(response)
	return 1
}

func NotifyTestAfterControllerRecv(recvID int, operationType string, object interface{}) {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	resourceType := getResourceTypeFromObj(object)
	name, namespace := extractNameNamespaceFromObj(object)
	resourceKey := generateResourceKey(resourceType, namespace, name)
	if !checkKVPairInTriggerObservationPoint(resourceKey, "when", "afterControllerRecv", false) {
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printSerializationError(err)
		return
	}
	log.Printf("NotifyTestAfterControllerRecv %s %s %s\n", operationType, resourceKey, string(jsonObject))
	request := &NotifyTestAfterControllerRecvRequest{
		OperationType: operationType,
		ResourceKey:   resourceKey,
		Object:        string(jsonObject),
	}
	var response Response
	err = rpcClient.Call("TestCoordinator.NotifyTestAfterControllerRecv", request, &response)
	if err != nil {
		printRPCError(err)
		return
	}
	checkResponse(response)
}

func NotifyTestBeforeCacheGet(key string, items []interface{}) {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	reconcilerType := getReconcilerFromStackTrace()
	if reconcilerType == UNKNOWN_RECONCILER_TYPE {
		return
	}
	if len(items) == 0 {
		return
	}
	resourceKey := path.Join(getResourceTypeFromObj(items[0]), key)
	log.Printf("NotifyTestBeforeCacheGet %s", resourceKey)
	NotifyTestBeforeCacheGetPause(resourceKey)
}

func NotifyTestAfterCacheGet(key string, item interface{}, exists bool) {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	if !exists {
		return
	}
	reconcilerType := getReconcilerFromStackTrace()
	if reconcilerType == UNKNOWN_RECONCILER_TYPE {
		return
	}
	resourceKey := path.Join(getResourceTypeFromObj(item), key)
	serializedObj, err := json.Marshal(item)
	if err != nil {
		printSerializationError(err)
		return
	}
	defer NotifyTestAfterCacheGetPause(resourceKey)
	if !checkKVPairInTriggerObservationPoint(resourceKey, "when", "afterControllerWrite", false) {
		return
	}
	if !checkKVPairInTriggerObservationPoint(resourceKey, "by", reconcilerType, false) {
		return
	}
	log.Printf("NotifyTestAfterCacheGet %s %s", resourceKey, string(serializedObj))
	request := &NotifyTestAfterControllerGetRequest{
		ResourceKey:    resourceKey,
		ReconcilerType: reconcilerType,
		Object:         string(serializedObj),
	}
	var response Response
	err = rpcClient.Call("TestCoordinator.NotifyTestAfterControllerGet", request, &response)
	if err != nil {
		printRPCError(err)
		return
	}
	checkResponse(response)
}

func NotifyTestBeforeCacheList(items []interface{}) {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	reconcilerType := getReconcilerFromStackTrace()
	if reconcilerType == UNKNOWN_RECONCILER_TYPE {
		return
	}
	if len(items) == 0 {
		return
	}
	resourceType := getResourceTypeFromObj(items[0])
	log.Printf("NotifyTestBeforeCacheList %s", resourceType)
	NotifyTestBeforeCacheListPause(resourceType)
}

func NotifyTestAfterCacheList(items []interface{}, listErr error) {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	if listErr != nil {
		return
	}
	if len(items) == 0 {
		return
	}
	reconcilerType := getReconcilerFromStackTrace()
	if reconcilerType == UNKNOWN_RECONCILER_TYPE {
		return
	}
	serializedObjList, err := json.Marshal(items)
	if err != nil {
		printSerializationError(err)
		return
	}
	resourceType := getResourceTypeFromObj(items[0])
	defer NotifyTestAfterCacheListPause(resourceType)
	if !checkKVPairInTriggerObservationPoint(resourceType, "when", "afterControllerWrite", true) {
		return
	}
	if !checkKVPairInTriggerObservationPoint(resourceType, "by", reconcilerType, true) {
		return
	}
	log.Printf("NotifyTestAfterCacheList %s %s", resourceType, string(serializedObjList))
	request := &NotifyTestAfterControllerListRequest{
		ResourceType:   resourceType,
		ReconcilerType: reconcilerType,
		ObjectList:     string(serializedObjList),
	}
	var response Response
	err = rpcClient.Call("TestCoordinator.NotifyTestAfterControllerList", request, &response)
	if err != nil {
		printRPCError(err)
		return
	}
	checkResponse(response)
}

func NotifyTestBeforeCacheGetPause(resourceKey string) {
	if !checkKVPairInAction("pauseController", "pauseScope", resourceKey, false) {
		return
	}
	if !checkKVPairInAction("pauseController", "pauseAt", "beforeControllerRead", false) && !checkKVPairInAction("pauseController", "pauseAt", "afterControllerRead", false) {
		return
	}
	log.Printf("NotifyTestBeforeCacheGetPause %s\n", resourceKey)
	request := &NotifyTestBeforeControllerReadPauseRequest{
		OperationType: GET,
		ResourceKey:   resourceKey,
	}
	var response Response
	err := rpcClient.Call("TestCoordinator.NotifyTestBeforeControllerReadPause", request, &response)
	if err != nil {
		printRPCError(err)
		return
	}
	checkResponse(response)
}

func NotifyTestAfterCacheGetPause(resourceKey string) {
	if !checkKVPairInAction("pauseController", "pauseScope", resourceKey, false) {
		return
	}
	if !checkKVPairInAction("pauseController", "pauseAt", "beforeControllerRead", false) && !checkKVPairInAction("pauseController", "pauseAt", "afterControllerRead", false) {
		return
	}
	log.Printf("NotifyTestAfterCacheGetPause %s\n", resourceKey)
	request := &NotifyTestAfterControllerReadPauseRequest{
		OperationType: GET,
		ResourceKey:   resourceKey,
	}
	var response Response
	err := rpcClient.Call("TestCoordinator.NotifyTestAfterControllerReadPause", request, &response)
	if err != nil {
		printRPCError(err)
		return
	}
	checkResponse(response)
}

func NotifyTestBeforeCacheListPause(resourceType string) {
	if !checkKVPairInAction("pauseController", "pauseScope", resourceType, true) {
		return
	}
	if !checkKVPairInAction("pauseController", "pauseAt", "beforeControllerRead", false) && !checkKVPairInAction("pauseController", "pauseAt", "afterControllerRead", false) {
		return
	}
	log.Printf("NotifyTestBeforeCacheListPause %s\n", resourceType)
	request := &NotifyTestBeforeControllerReadPauseRequest{
		OperationType: LIST,
		ResourceType:  resourceType,
	}
	var response Response
	err := rpcClient.Call("TestCoordinator.NotifyTestBeforeControllerReadPause", request, &response)
	if err != nil {
		printRPCError(err)
		return
	}
	checkResponse(response)
}

func NotifyTestAfterCacheListPause(resourceType string) {
	if !checkKVPairInAction("pauseController", "pauseScope", resourceType, true) {
		return
	}
	if !checkKVPairInAction("pauseController", "pauseAt", "beforeControllerRead", false) && !checkKVPairInAction("pauseController", "pauseAt", "afterControllerRead", false) {
		return
	}
	log.Printf("NotifyTestAfterCacheListPause %s\n", resourceType)
	request := &NotifyTestAfterControllerReadPauseRequest{
		OperationType: LIST,
		ResourceType:  resourceType,
	}
	var response Response
	err := rpcClient.Call("TestCoordinator.NotifyTestAfterControllerReadPause", request, &response)
	if err != nil {
		printRPCError(err)
		return
	}
	checkResponse(response)
}

func NotifyTestBeforeRestCall(verb string, pathPrefix string, subpath string, namespace string, namespaceSet bool, resourceType string, resourceName string, subresource string, object interface{}) int {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return 1
	}
	if err := initRPCClient(); err != nil {
		return 1
	}
	reconcilerType := getReconcilerFromStackTrace()
	if reconcilerType == UNKNOWN_RECONCILER_TYPE {
		return 1
	}
	serializedObj, err := json.Marshal(object)
	if err != nil {
		printSerializationError(err)
		return 1
	}
	controllerOperationType := HttpVerbToControllerOperation(verb, resourceName, subresource)
	if controllerOperationType == UNKNOWN {
		log.Println("Unknown operation")
	} else if controllerOperationType == GET || controllerOperationType == LIST {
		log.Println("Get and List not supported yet")
	} else {
		resourceKey := generateResourceKeyFromRestCall(verb, resourceType, namespace, resourceName, object)
		defer NotifyTestBeforeControllerWritePause(controllerOperationType, resourceKey)
		if !checkKVPairInTriggerObservationPoint(resourceKey, "when", "beforeControllerWrite", false) {
			return -1
		}
		if !checkKVPairInTriggerObservationPoint(resourceKey, "by", reconcilerType, false) {
			return -1
		}
		log.Printf("NotifyTestBeforeRestWrite %s %s %s %s %s %s\n", verb, resourceKey, reconcilerType, pathPrefix, subpath, string(serializedObj))
		request := &NotifyTestBeforeControllerWriteRequest{
			WriteType:      controllerOperationType,
			ResourceKey:    resourceKey,
			ReconcilerType: reconcilerType,
			Object:         string(serializedObj),
		}
		var response Response
		err = rpcClient.Call("TestCoordinator.NotifyTestBeforeControllerWrite", request, &response)
		if err != nil {
			printRPCError(err)
			return 1
		}
		checkResponse(response)
	}
	return 1
}

func NotifyTestAfterRestCall(controllerOperationID int, verb string, pathPrefix string, subpath string, namespace string, namespaceSet bool, resourceType string, resourceName string, subresource string, object interface{}, serializationErr error, respErr error) {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return
	}
	if serializationErr != nil {
		return
	}
	if respErr != nil {
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
	controllerOperationType := HttpVerbToControllerOperation(verb, resourceName, subresource)
	if controllerOperationType == UNKNOWN {
		log.Println("Unknown operation")
	} else if controllerOperationType == GET || controllerOperationType == LIST {
		log.Println("Get and List not supported yet")
	} else {
		resourceKey := generateResourceKeyFromRestCall(verb, resourceType, namespace, resourceName, object)
		defer NotifyTestAfterControllerWritePause(controllerOperationType, resourceKey)
		if !checkKVPairInTriggerObservationPoint(resourceKey, "when", "afterControllerWrite", false) {
			return
		}
		if !checkKVPairInTriggerObservationPoint(resourceKey, "by", reconcilerType, false) {
			return
		}
		log.Printf("NotifyTestAfterRestWrite %s %s %s %s %s %s\n", verb, resourceKey, reconcilerType, pathPrefix, subpath, string(serializedObj))
		request := &NotifyTestAfterControllerWriteRequest{
			WriteType:      controllerOperationType,
			ReconcilerType: reconcilerType,
			ResourceKey:    resourceKey,
			Object:         string(serializedObj),
		}
		var response Response
		err = rpcClient.Call("TestCoordinator.NotifyTestAfterControllerWrite", request, &response)
		if err != nil {
			printRPCError(err)
			return
		}
		checkResponse(response)
	}
}

func NotifyTestBeforeControllerWritePause(writeType string, resourceKey string) {
	// NOTE: assume the caller has checked the config and created the client
	if !checkKVPairInAction("pauseController", "pauseScope", resourceKey, false) {
		return
	}
	if !checkKVPairInAction("pauseController", "pauseAt", "beforeControllerWrite", false) && !checkKVPairInAction("pauseController", "pauseAt", "afterControllerWrite", false) {
		return
	}
	log.Printf("NotifyTestBeforeControllerWritePause %s %s\n", writeType, resourceKey)
	request := &NotifyTestBeforeControllerWritePauseRequest{
		WriteType:   writeType,
		ResourceKey: resourceKey,
	}
	var response Response
	err := rpcClient.Call("TestCoordinator.NotifyTestBeforeControllerWritePause", request, &response)
	if err != nil {
		printRPCError(err)
		return
	}
	checkResponse(response)
}

func NotifyTestAfterControllerWritePause(writeType string, resourceKey string) {
	// NOTE: assume the caller has checked the config and created the client
	if !checkKVPairInAction("pauseController", "pauseScope", resourceKey, false) {
		return
	}
	if !checkKVPairInAction("pauseController", "pauseAt", "beforeControllerWrite", false) && !checkKVPairInAction("pauseController", "pauseAt", "afterControllerWrite", false) {
		return
	}
	log.Printf("NotifyTestAfterControllerWritePause %s %s\n", writeType, resourceKey)
	request := &NotifyTestAfterControllerWritePauseRequest{
		WriteType:   writeType,
		ResourceKey: resourceKey,
	}
	var response Response
	err := rpcClient.Call("TestCoordinator.NotifyTestAfterControllerWritePause", request, &response)
	if err != nil {
		printRPCError(err)
		return
	}
	checkResponse(response)
}

func NotifyTestBeforeAnnotatedAPICall(moduleName string, filePath string, receiverType string, funName string) int {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return -1
	}
	if err := initRPCClient(); err != nil {
		return -1
	}
	if !checkKVPairInAnnotatedAPICallTriggerCondition(receiverType + funName) {
		return -1
	}
	reconcilerType := getReconcilerFromStackTrace()
	log.Printf("NotifyTestBeforeAnnotatedAPICall %s %s %s %s\n", moduleName, filePath, receiverType, funName)
	request := &NotifyTestBeforeAnnotatedAPICallRequest{
		ModuleName:     moduleName,
		FilePath:       filePath,
		ReceiverType:   receiverType,
		FunName:        funName,
		ReconcilerType: reconcilerType,
	}
	var response Response
	err := rpcClient.Call("TestCoordinator.NotifyTestBeforeAnnotatedAPICall", request, &response)
	if err != nil {
		printRPCError(err)
		return -1
	}
	checkResponse(response)
	return 1
}

func NotifyTestAfterAnnotatedAPICall(invocationID int, moduleName string, filePath string, receiverType string, funName string) {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	if !checkKVPairInAnnotatedAPICallTriggerCondition(receiverType + funName) {
		return
	}
	reconcilerType := getReconcilerFromStackTrace()
	log.Printf("NotifyTestAfterAnnotatedAPICall %s %s %s %s\n", moduleName, filePath, receiverType, funName)
	request := &NotifyTestAfterAnnotatedAPICallRequest{
		ModuleName:     moduleName,
		FilePath:       filePath,
		ReceiverType:   receiverType,
		FunName:        funName,
		ReconcilerType: reconcilerType,
	}
	var response Response
	err := rpcClient.Call("TestCoordinator.NotifyTestAfterAnnotatedAPICall", request, &response)
	if err != nil {
		printRPCError(err)
		return
	}
	checkResponse(response)
}

func NotifyTestBeforeAPIServerRecv(eventType, key string, object interface{}) {
	if err := loadSieveConfigFromConfigMap(eventType, key, object, true); err != nil {
		return
	}
	// we should log the API event before initializing the client
	LogAPIEvent(eventType, key, object)
	if err := initRPCClient(); err != nil {
		return
	}
	if err := initAPIServerHostName(); err != nil {
		return
	}
	resourceType := getResourceTypeFromObj(object)
	namespace, name, err := getResourceNamespaceNameFromAPIKey(key)
	if err != nil {
		return
	}
	resourceKey := generateResourceKey(resourceType, namespace, name)
	if !checkKVPairInTriggerObservationPoint(resourceKey, "when", "beforeAPIServerRecv", false) {
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printSerializationError(err)
		return
	}
	log.Printf("NotifyTestBeforeAPIServerRecv %s %s %s\n", eventType, resourceKey, string(jsonObject))
	request := &NotifyTestBeforeAPIServerRecvRequest{
		APIServerHostname: apiserverHostname,
		OperationType:     eventType,
		ResourceKey:       resourceKey,
		Object:            string(jsonObject),
	}
	var response Response
	err = rpcClient.Call("TestCoordinator.NotifyTestBeforeAPIServerRecv", request, &response)
	if err != nil {
		printRPCError(err)
		return
	}
	checkResponse(response)
}

func NotifyTestAfterAPIServerRecv(eventType, key string, object interface{}) {
	if err := loadSieveConfigFromConfigMap(eventType, key, object, true); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	if err := initAPIServerHostName(); err != nil {
		return
	}
	resourceType := getResourceTypeFromObj(object)
	namespace, name, err := getResourceNamespaceNameFromAPIKey(key)
	if err != nil {
		return
	}
	resourceKey := generateResourceKey(resourceType, namespace, name)
	if !checkKVPairInTriggerObservationPoint(resourceKey, "when", "afterAPIServerRecv", false) {
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printSerializationError(err)
		return
	}
	log.Printf("NotifyTestAfterAPIServerRecv %s %s %s\n", eventType, resourceKey, string(jsonObject))
	request := &NotifyTestAfterAPIServerRecvRequest{
		APIServerHostname: apiserverHostname,
		OperationType:     eventType,
		ResourceKey:       resourceKey,
		Object:            string(jsonObject),
	}
	var response Response
	err = rpcClient.Call("TestCoordinator.NotifyTestAfterAPIServerRecv", request, &response)
	if err != nil {
		printRPCError(err)
		return
	}
	checkResponse(response)
}
