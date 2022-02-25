package sieve

import (
	"encoding/json"
	"log"

	"k8s.io/apimachinery/pkg/types"
)

func NotifyTestBeforeControllerRecv(operationType string, object interface{}) {
	if err := loadSieveConfigFromEnv(); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	resourceType := regularizeType(object)
	name, namespace := extractNameNamespaceFromObj(object)
	resourceKey := generateResourceKey(resourceType, namespace, name)
	if !checkKVPairInTriggerCondition(resourceKey, "conditionType", "beforeControllerRecv", false) {
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return
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
		return
	}
	checkResponse(response, "NotifyTestBeforeControllerRecv")
}

func NotifyTestAfterControllerRecv(operationType string, object interface{}) {
	if err := loadSieveConfigFromEnv(); err != nil {
		return
	}
	if err := initRPCClient(); err != nil {
		return
	}
	resourceType := regularizeType(object)
	name, namespace := extractNameNamespaceFromObj(object)
	resourceKey := generateResourceKey(resourceType, namespace, name)
	if !checkKVPairInTriggerCondition(resourceKey, "conditionType", "afterControllerRecv", false) {
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
	if err := loadSieveConfigFromEnv(); err != nil {
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
	if err := loadSieveConfigFromEnv(); err != nil {
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

func NotifyTestAfterControllerWrite(writeID int, writeType string, object interface{}, k8sErr error) {
	if err := loadSieveConfigFromEnv(); err != nil {
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
		WriteID:        writeID,
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

func NotifyTestBeforeAPIServerRecv(eventType, key string, object interface{}) {
	if err := loadSieveConfigFromConfigMap(eventType, key, object); err != nil {
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

	// if !checkKVPairInAction("pauseAPIServer", "serverName", apiserverHostname) {
	// 	return
	// }
	// if !checkKVPairInAction("pauseAPIServer", "watchName", resourceType) {
	// 	return
	// }
	// Ask test coordinator whether to pause here
	// log.Println("Ask test coordinator whether to pause here")
}

func NotifyTestAfterAPIServerRecv(eventType, key string, object interface{}) {
	if err := loadSieveConfigFromConfigMap(eventType, key, object); err != nil {
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
