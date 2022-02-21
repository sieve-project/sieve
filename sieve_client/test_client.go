package sieve

import (
	"encoding/json"
	"log"
	"strings"

	"k8s.io/apimachinery/pkg/types"
)

func NotifyTestBeforeControllerRecv(operationType string, object interface{}) {
	if err := loadSieveConfigFromEnv(); err != nil {
		return
	}
	resourceType := regularizeType(object)
	name, namespace := extractNameNamespaceFromObj(object)
	resourcekey := generateResourceKey(resourceType, namespace, name)
	if _, ok := watchSet[resourcekey]; !ok {
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return
	}
	log.Printf("NotifyTestBeforeControllerRecv %s %s %s\n", operationType, resourcekey, string(jsonObject))
	// client, err := newClient()
	// if err != nil {
	// 	printError(err, SIEVE_CONN_ERR)
	// 	return
	// }
	// defer client.Close()
	// request := &NotifyTestBeforeControllerRecvRequest{
	// 	OperationType: operationType,
	// 	ResourceKey:   resourcekey,
	// 	Object:        string(jsonObject),
	// }
	// var response Response
	// err = client.Call("TestListener.NotifyTestBeforeControllerRecv", request, &response)
	// if err != nil {
	// 	printError(err, SIEVE_REPLY_ERR)
	// 	return
	// }
	// checkResponse(response, "NotifyTestBeforeControllerRecv")
	// client.Close()
}

func NotifyTestAfterControllerRecv(operationType string, object interface{}) {
	if err := loadSieveConfigFromEnv(); err != nil {
		return
	}
	resourceType := regularizeType(object)
	name, namespace := extractNameNamespaceFromObj(object)
	resourcekey := generateResourceKey(resourceType, namespace, name)
	if _, ok := watchSet[resourcekey]; !ok {
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return
	}
	log.Printf("NotifyTestAfterControllerRecv %s %s %s\n", operationType, resourcekey, string(jsonObject))
	// client, err := newClient()
	// if err != nil {
	// 	printError(err, SIEVE_CONN_ERR)
	// 	return
	// }
	// defer client.Close()
	// request := &NotifyTestAfterControllerRecvRequest{
	// 	OperationType: operationType,
	// 	ResourceKey:   resourcekey,
	// 	Object:        string(jsonObject),
	// }
	// var response Response
	// err = client.Call("TestListener.NotifyTestAfterControllerRecv", request, &response)
	// if err != nil {
	// 	printError(err, SIEVE_REPLY_ERR)
	// 	return
	// }
	// checkResponse(response, "NotifyTestAfterControllerRecv")
	// client.Close()
}

func NotifyTestAfterControllerGet(readType string, fromCache bool, namespacedName types.NamespacedName, object interface{}, k8sErr error) {
	if err := loadSieveConfigFromEnv(); err != nil {
		return
	}
	if k8sErr != nil {
		return
	}
	// reconcilerType := getReconcilerFromStackTrace()
	resourceType := regularizeType(object)
	resourceKey := generateResourceKey(resourceType, namespacedName.Namespace, namespacedName.Name)
	if _, ok := watchSet[resourceKey]; !ok {
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return
	}
	log.Printf("NotifyTestAfterControllerGet %s %s %s\n", readType, resourceKey, string(jsonObject))
	// client, err := newClient()
	// if err != nil {
	// 	printError(err, SIEVE_CONN_ERR)
	// 	return
	// }
	// defer client.Close()
	// request := &NotifyTestAfterControllerGetRequest{
	// 	ResourceKey:    resourceKey,
	// 	ReconcilerType: reconcilerType,
	// 	Object:         string(jsonObject),
	// }
	// var response Response
	// err = client.Call("TestListener.NotifyTestAfterControllerGet", request, &response)
	// if err != nil {
	// 	printError(err, SIEVE_REPLY_ERR)
	// 	return
	// }
	// checkResponse(response, "NotifyTestAfterControllerGet")
}

func NotifyTestAfterControllerList(readType string, fromCache bool, object interface{}, k8sErr error) {
	if err := loadSieveConfigFromEnv(); err != nil {
		return
	}
	if k8sErr != nil {
		return
	}
	// reconcilerType := getReconcilerFromStackTrace()
	resourceType := regularizeType(object)
	skip := false
	for key := range watchSet {
		if strings.HasPrefix(key, resourceType+"/") {
			skip = true
		}
	}
	if skip {
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return
	}
	log.Printf("NotifyTestAfterControllerGet %s %s %s\n", readType, resourceType, string(jsonObject))
	// client, err := newClient()
	// if err != nil {
	// 	printError(err, SIEVE_CONN_ERR)
	// 	return
	// }
	// defer client.Close()
	// request := &NotifyTestAfterControllerListRequest{
	// 	ResourceType:   resourceType,
	// 	ReconcilerType: reconcilerType,
	// 	ObjectList:     string(jsonObject),
	// }
	// var response Response
	// err = client.Call("TestListener.NotifyTestAfterControllerList", request, &response)
	// if err != nil {
	// 	printError(err, SIEVE_REPLY_ERR)
	// 	return
	// }
	// checkResponse(response, "NotifyTestAfterControllerList")
}

func NotifyTestAfterControllerWrite(writeID int, writeType string, object interface{}, k8sErr error) {
	if err := loadSieveConfigFromEnv(); err != nil {
		return
	}
	if k8sErr != nil {
		return
	}
	// reconcilerType := getReconcilerFromStackTrace()
	resourceType := regularizeType(object)
	name, namespace := extractNameNamespaceFromObj(object)
	resourceKey := generateResourceKey(resourceType, namespace, name)
	if _, ok := watchSet[resourceKey]; !ok {
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, SIEVE_JSON_ERR)
		return
	}
	log.Printf("NotifyTestAfterControllerWrite %s %s %s\n", writeType, resourceKey, string(jsonObject))
	// client, err := newClient()
	// if err != nil {
	// 	printError(err, SIEVE_CONN_ERR)
	// 	return
	// }
	// defer client.Close()
	// request := &NotifyTestAfterControllerWriteRequest{
	// 	writeID:        writeID,
	// 	writeType:      writeType,
	// 	ResourceKey:    resourceKey,
	// 	ReconcilerType: reconcilerType,
	// 	Object:         string(jsonObject),
	// }
	// var response Response
	// err = client.Call("TestListener.NotifyTestAfterControllerWrite", request, &response)
	// if err != nil {
	// 	printError(err, SIEVE_REPLY_ERR)
	// 	return
	// }
	// checkResponse(response, "NotifyTestAfterControllerWrite")
}

func NotifyTestBeforeAPIServerRecv(eventType, key string, object interface{}) {
	if err := loadSieveConfigFromConfigMap(eventType, key, object); err != nil {
		return
	}
	tokens := strings.Split(key, "/")
	namespace := tokens[len(tokens)-2]
	if namespace == "default" {
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

func NotifyTestAfterAPIServerRecv(eventType, key string, object interface{}) {
	if err := loadSieveConfigFromConfigMap(eventType, key, object); err != nil {
		return
	}
}
