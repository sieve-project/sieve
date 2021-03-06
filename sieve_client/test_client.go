package sieve

import (
	"encoding/json"
	"log"
	"strings"

	"k8s.io/apimachinery/pkg/types"
)

func NotifyTestBeforeControllerRecv(operationType string, object interface{}) int {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return -1
	}
	if err := initRPCClient(); err != nil {
		return -1
	}
	resourceType := regularizeType(object)
	name, namespace := extractNameNamespaceFromObj(object)
	resourceKey := generateResourceKey(resourceType, namespace, name)
	if !checkKVPairInTriggerObservationPoint(resourceKey, "when", "beforeControllerRecv", false) {
		return -1
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
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
		printError(err, SIEVE_REPLY_ERR)
		return -1
	}
	checkResponse(response, "NotifyTestBeforeControllerRecv")
	return 1
}

func NotifyTestAfterControllerRecv(recvID int, operationType string, object interface{}) {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	resourceType := regularizeType(object)
	name, namespace := extractNameNamespaceFromObj(object)
	resourceKey := generateResourceKey(resourceType, namespace, name)
	if !checkKVPairInTriggerObservationPoint(resourceKey, "when", "afterControllerRecv", false) {
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
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
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyTestAfterControllerRecv")
}

func NotifyTestAfterControllerGet(readType string, fromCache bool, namespacedName types.NamespacedName, object interface{}, k8sErr error) {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return
	}
	if k8sErr != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	reconcilerType := getReconcilerFromStackTrace()
	resourceType := regularizeType(object)
	resourceKey := generateResourceKey(resourceType, namespacedName.Namespace, namespacedName.Name)
	if !checkKVPairInTriggerObservationPoint(resourceKey, "when", "afterControllerWrite", false) {
		return
	}
	if !checkKVPairInTriggerObservationPoint(resourceKey, "by", reconcilerType, false) {
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return
	}
	log.Printf("NotifyTestAfterControllerGet %s %s %s\n", readType, resourceKey, string(jsonObject))
	request := &NotifyTestAfterControllerGetRequest{
		ResourceKey:    resourceKey,
		ReconcilerType: reconcilerType,
		Object:         string(jsonObject),
	}
	var response Response
	err = rpcClient.Call("TestCoordinator.NotifyTestAfterControllerGet", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyTestAfterControllerGet")
}

func NotifyTestAfterControllerList(readType string, fromCache bool, object interface{}, k8sErr error) {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return
	}
	if k8sErr != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	reconcilerType := getReconcilerFromStackTrace()
	unTrimmedResourceType := regularizeType(object)
	resourceType := strings.TrimSuffix(unTrimmedResourceType, "list")
	if !checkKVPairInTriggerObservationPoint(resourceType, "when", "afterControllerWrite", true) {
		return
	}
	if !checkKVPairInTriggerObservationPoint(resourceType, "by", reconcilerType, true) {
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return
	}
	log.Printf("NotifyTestAfterControllerGet %s %s %s\n", readType, resourceType, string(jsonObject))
	request := &NotifyTestAfterControllerListRequest{
		ResourceType:   resourceType,
		ReconcilerType: reconcilerType,
		ObjectList:     string(jsonObject),
	}
	var response Response
	err = rpcClient.Call("TestCoordinator.NotifyTestAfterControllerList", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyTestAfterControllerList")
}

func NotifyTestBeforeControllerWrite(writeType string, object interface{}) int {
	if err := loadSieveConfigFromEnv(false); err != nil {
		return -1
	}
	if err := initRPCClient(); err != nil {
		return -1
	}
	reconcilerType := getReconcilerFromStackTrace()
	resourceType := regularizeType(object)
	name, namespace := extractNameNamespaceFromObj(object)
	resourceKey := generateResourceKey(resourceType, namespace, name)
	defer NotifyTestBeforeControllerWritePause(writeType, resourceKey)
	if !checkKVPairInTriggerObservationPoint(resourceKey, "when", "beforeControllerWrite", false) {
		return -1
	}
	if !checkKVPairInTriggerObservationPoint(resourceKey, "by", reconcilerType, false) {
		return -1
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return -1
	}
	log.Printf("NotifyTestBeforeControllerWrite %s %s %s\n", writeType, resourceKey, string(jsonObject))
	request := &NotifyTestBeforeControllerWriteRequest{
		WriteType:      writeType,
		ResourceKey:    resourceKey,
		ReconcilerType: reconcilerType,
		Object:         string(jsonObject),
	}
	var response Response
	err = rpcClient.Call("TestCoordinator.NotifyTestBeforeControllerWrite", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return -1
	}
	checkResponse(response, "NotifyTestBeforeControllerWrite")
	return 1
}

func NotifyTestAfterControllerWrite(writeID int, writeType string, object interface{}, k8sErr error) {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return
	}
	if k8sErr != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	reconcilerType := getReconcilerFromStackTrace()
	resourceType := regularizeType(object)
	name, namespace := extractNameNamespaceFromObj(object)
	resourceKey := generateResourceKey(resourceType, namespace, name)
	defer NotifyTestAfterControllerWritePause(writeType, resourceKey)
	if !checkKVPairInTriggerObservationPoint(resourceKey, "when", "afterControllerWrite", false) {
		return
	}
	if !checkKVPairInTriggerObservationPoint(resourceKey, "by", reconcilerType, false) {
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return
	}
	log.Printf("NotifyTestAfterControllerWrite %s %s %s\n", writeType, resourceKey, string(jsonObject))
	request := &NotifyTestAfterControllerWriteRequest{
		WriteType:      writeType,
		ResourceKey:    resourceKey,
		ReconcilerType: reconcilerType,
		Object:         string(jsonObject),
	}
	var response Response
	err = rpcClient.Call("TestCoordinator.NotifyTestAfterControllerWrite", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyTestAfterControllerWrite")
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
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyTestBeforeControllerWritePause")
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
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyTestAfterControllerWritePause")
}

func NotifyTestBeforeControllerGetPause(readType string, namespacedName types.NamespacedName, object interface{}) {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	resourceType := regularizeType(object)
	resourceKey := generateResourceKey(resourceType, namespacedName.Namespace, namespacedName.Name)
	if !checkKVPairInAction("pauseController", "pauseScope", resourceKey, false) {
		return
	}
	if !checkKVPairInAction("pauseController", "pauseAt", "beforeControllerRead", false) && !checkKVPairInAction("pauseController", "pauseAt", "afterControllerRead", false) {
		return
	}
	log.Printf("NotifyTestBeforeControllerGetPause %s %s\n", readType, resourceKey)
	request := &NotifyTestBeforeControllerReadPauseRequest{
		OperationType: "Get",
		ResourceKey:   resourceKey,
	}
	var response Response
	err := rpcClient.Call("TestCoordinator.NotifyTestBeforeControllerReadPause", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyTestBeforeControllerGetPause")
}

func NotifyTestAfterControllerGetPause(readType string, namespacedName types.NamespacedName, object interface{}) {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	resourceType := regularizeType(object)
	resourceKey := generateResourceKey(resourceType, namespacedName.Namespace, namespacedName.Name)
	if !checkKVPairInAction("pauseController", "pauseScope", resourceKey, false) {
		return
	}
	if !checkKVPairInAction("pauseController", "pauseAt", "beforeControllerRead", false) && !checkKVPairInAction("pauseController", "pauseAt", "afterControllerRead", false) {
		return
	}
	log.Printf("NotifyTestAfterControllerGetPause %s %s\n", readType, resourceKey)
	request := &NotifyTestAfterControllerReadPauseRequest{
		OperationType: "Get",
		ResourceKey:   resourceKey,
	}
	var response Response
	err := rpcClient.Call("TestCoordinator.NotifyTestAfterControllerReadPause", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyTestAfterControllerGetPause")
}

func NotifyTestBeforeControllerListPause(readType string, object interface{}) {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	unTrimmedResourceType := regularizeType(object)
	resourceType := strings.TrimSuffix(unTrimmedResourceType, "list")
	if !checkKVPairInAction("pauseController", "pauseScope", resourceType, true) {
		return
	}
	if !checkKVPairInAction("pauseController", "pauseAt", "beforeControllerRead", false) && !checkKVPairInAction("pauseController", "pauseAt", "afterControllerRead", false) {
		return
	}
	log.Printf("NotifyTestBeforeControllerListPause %s %s\n", readType, resourceType)
	request := &NotifyTestBeforeControllerReadPauseRequest{
		OperationType: "List",
		ResourceType:  resourceType,
	}
	var response Response
	err := rpcClient.Call("TestCoordinator.NotifyTestBeforeControllerReadPause", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyTestBeforeControllerListPause")
}

func NotifyTestAfterControllerListPause(readType string, object interface{}) {
	if err := loadSieveConfigFromEnv(true); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	unTrimmedResourceType := regularizeType(object)
	resourceType := strings.TrimSuffix(unTrimmedResourceType, "list")
	if !checkKVPairInAction("pauseController", "pauseScope", resourceType, true) {
		return
	}
	if !checkKVPairInAction("pauseController", "pauseAt", "beforeControllerRead", false) && !checkKVPairInAction("pauseController", "pauseAt", "afterControllerRead", false) {
		return
	}
	log.Printf("NotifyTestAfterControllerListPause %s %s\n", readType, resourceType)
	request := &NotifyTestAfterControllerReadPauseRequest{
		OperationType: "List",
		ResourceType:  resourceType,
	}
	var response Response
	err := rpcClient.Call("TestCoordinator.NotifyTestAfterControllerReadPause", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyTestAfterControllerListPause")
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
		printError(err, SIEVE_REPLY_ERR)
		return -1
	}
	checkResponse(response, "NotifyTestBeforeAnnotatedAPICall")
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
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyTestAfterAnnotatedAPICall")
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
	resourceType := regularizeType(object)
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
		printError(err, SIEVE_JSON_ERR)
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
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyTestBeforeAPIServerRecv")
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
	resourceType := regularizeType(object)
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
		printError(err, SIEVE_JSON_ERR)
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
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyTestAfterAPIServerRecv")
}
