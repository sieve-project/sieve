package sieve

import (
	"encoding/json"
	"log"
	"os"
	"strings"

	"k8s.io/apimachinery/pkg/api/errors"
)

func NotifyTimeTravelAfterProcessEvent(eventType, key string, object interface{}) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if checkTimeTravelTiming("after") {
		// log.Printf("[sieve] NotifyTimeTravelAfterProcessEvent")
		NotifyTimeTravelAboutProcessEvent(eventType, key, object)
	}
}

func NotifyTimeTravelBeforeProcessEvent(eventType, key string, object interface{}) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	tokens := strings.Split(key, "/")
	namespace := tokens[len(tokens)-2]
	if namespace == config["ce-namespace"].(string) {
		if !checkStage(TEST) || !checkMode(TIME_TRAVEL) {
			return
		}
		jsonObject, err := json.Marshal(object)
		if err != nil {
			printError(err, SIEVE_JSON_ERR)
			return
		}
		log.Printf("[SIEVE-API-EVENT]\t%s\t%s\t%s\n", eventType, key, string(jsonObject))
	}
	if checkTimeTravelTiming("before") {
		// log.Printf("[sieve] NotifyTimeTravelBeforeProcessEvent")
		NotifyTimeTravelAboutProcessEvent(eventType, key, object)
	}
}

func NotifyTimeTravelAboutProcessEvent(eventType, key string, object interface{}) {
	tokens := strings.Split(key, "/")
	if len(tokens) < 4 {
		return
	}
	// TODO: implement a method to map from apiKey to rType, namespace and name
	resourceType := pluralToSingle(tokens[len(tokens)-3])
	// Ref: https://github.com/kubernetes/kubernetes/blob/master/pkg/kubeapiserver/default_storage_factory_builder.go#L40
	prev := tokens[len(tokens)-4]
	cur := tokens[len(tokens)-3]
	if prev == "services" && cur == "endpoints" {
		resourceType = "endpoints"
	}
	if prev == "services" && cur == "specs" {
		resourceType = "service"
	}
	namespace := tokens[len(tokens)-2]
	name := tokens[len(tokens)-1]
	if name == config["ce-name"].(string) && namespace == config["ce-namespace"].(string) && resourceType == config["ce-rtype"].(string) {
		log.Printf("[sieve] NotifyTimeTravelAboutProcessEvent, eventType: %s, key: %s, resourceType: %s, namespace: %s, name: %s", eventType, key, resourceType, namespace, name)
		log.Printf("[sieve][rt-ns-name][curcial-event] %s %s %s", resourceType, namespace, name)
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
		hostname, err := os.Hostname()
		if err != nil {
			printError(err, SIEVE_HOST_ERR)
			return
		}
		request := &NotifyTimeTravelCrucialEventRequest{
			Hostname:  hostname,
			EventType: eventType,
			Object:    string(jsonObject),
		}
		var response Response
		err = client.Call("TimeTravelListener.NotifyTimeTravelCrucialEvent", request, &response)
		if err != nil {
			printError(err, SIEVE_REPLY_ERR)
			return
		}
		checkResponse(response, "NotifyTimeTravelCrucialEvent")
		client.Close()
	} else if name == config["se-name"].(string) && namespace == config["se-namespace"].(string) && resourceType == config["se-rtype"].(string) && eventType == config["se-etype"] {
		log.Printf("[sieve] NotifyTimeTravelAboutProcessEvent, eventType: %s, key: %s, resourceType: %s, namespace: %s, name: %s", eventType, key, resourceType, namespace, name)
		log.Printf("[sieve][rt-ns-name][side-effect] %s %s %s", resourceType, namespace, name)
		client, err := newClient()
		if err != nil {
			printError(err, SIEVE_CONN_ERR)
			return
		}
		hostname, err := os.Hostname()
		if err != nil {
			printError(err, SIEVE_HOST_ERR)
			return
		}
		request := &NotifyTimeTravelRestartPointRequest{
			Hostname:     hostname,
			EventType:    eventType,
			ResourceType: resourceType,
			Name:         name,
			Namespace:    namespace,
		}
		var response Response
		err = client.Call("TimeTravelListener.NotifyTimeTravelRestartPoint", request, &response)
		if err != nil {
			printError(err, SIEVE_REPLY_ERR)
			return
		}
		checkResponse(response, "NotifyTimeTravelRestartPoint")
		client.Close()
	}
}

func NotifyTimeTravelAfterSideEffects(sideEffectID int, sideEffectType string, object interface{}, k8sErr error) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(TEST) || !checkMode(TIME_TRAVEL) {
		return
	}
	// log.Printf("[sieve][NotifyTimeTravelAfterSideEffects] %s %v\n", sideEffectType, object)
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
	request := &NotifyTimeTravelAfterSideEffectsRequest{
		SideEffectID:   sideEffectID,
		SideEffectType: sideEffectType,
		Object:         string(jsonObject),
		ResourceType:   regularizeType(object),
		Error:          errorString,
	}
	var response Response
	err = client.Call("TimeTravelListener.NotifyTimeTravelAfterSideEffects", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyTimeTravelAfterSideEffects")
	client.Close()
}
