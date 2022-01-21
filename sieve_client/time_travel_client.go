package sieve

import (
	"encoding/json"
	"log"
	"os"
	"strings"

	"k8s.io/apimachinery/pkg/api/errors"
)

func NotifyStaleStateAfterProcessEvent(eventType, key string, object interface{}) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if checkStaleStateTiming("after") {
		// log.Printf("[sieve] NotifyStaleStateAfterProcessEvent")
		NotifyStaleStateAboutProcessEvent(eventType, key, object)
	}
}

func NotifyStaleStateBeforeProcessEvent(eventType, key string, object interface{}) {
	loadSieveConfigMap(eventType, key, object)
	if err := loadSieveConfig(); err != nil {
		return
	}
	tokens := strings.Split(key, "/")
	namespace := tokens[len(tokens)-2]
	if namespace == config["ce-namespace"].(string) {
		if !checkStage(TEST) || !checkMode(STALE_STATE) {
			return
		}
		jsonObject, err := json.Marshal(object)
		if err != nil {
			printError(err, SIEVE_JSON_ERR)
			return
		}
		// TODO: instead of printing key, we should parse out name, namespace and rtype here
		log.Printf("[SIEVE-API-EVENT]\t%s\t%s\t%s\n", eventType, key, string(jsonObject))
	}
	if checkStaleStateTiming("before") {
		// log.Printf("[sieve] NotifyStaleStateBeforeProcessEvent")
		NotifyStaleStateAboutProcessEvent(eventType, key, object)
	}
}

func NotifyStaleStateAboutProcessEvent(eventType, key string, object interface{}) {
	tokens := strings.Split(key, "/")
	if len(tokens) < 4 {
		return
	}
	resourceType := regularizeType(object)
	namespace := tokens[len(tokens)-2]
	name := tokens[len(tokens)-1]
	if name == config["ce-name"].(string) && namespace == config["ce-namespace"].(string) && resourceType == config["ce-rtype"].(string) {
		log.Printf("[sieve] NotifyStaleStateAboutProcessEvent, eventType: %s, key: %s, resourceType: %s, namespace: %s, name: %s", eventType, key, resourceType, namespace, name)
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
		request := &NotifyStaleStateCrucialEventRequest{
			Hostname:  hostname,
			EventType: eventType,
			Object:    string(jsonObject),
		}
		var response Response
		err = client.Call("StaleStateListener.NotifyStaleStateCrucialEvent", request, &response)
		if err != nil {
			printError(err, SIEVE_REPLY_ERR)
			return
		}
		checkResponse(response, "NotifyStaleStateCrucialEvent")
		client.Close()
	} else if name == config["se-name"].(string) && namespace == config["se-namespace"].(string) && resourceType == config["se-rtype"].(string) && eventType == config["se-etype"] {
		log.Printf("[sieve] NotifyStaleStateAboutProcessEvent, eventType: %s, key: %s, resourceType: %s, namespace: %s, name: %s", eventType, key, resourceType, namespace, name)
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
		request := &NotifyStaleStateRestartPointRequest{
			Hostname:     hostname,
			EventType:    eventType,
			ResourceType: resourceType,
			Name:         name,
			Namespace:    namespace,
		}
		var response Response
		err = client.Call("StaleStateListener.NotifyStaleStateRestartPoint", request, &response)
		if err != nil {
			printError(err, SIEVE_REPLY_ERR)
			return
		}
		checkResponse(response, "NotifyStaleStateRestartPoint")
		client.Close()
	}
}

func NotifyStaleStateAfterSideEffects(sideEffectID int, sideEffectType string, object interface{}, k8sErr error) {
	if err := loadSieveConfig(); err != nil {
		return
	}
	if !checkStage(TEST) || !checkMode(STALE_STATE) {
		return
	}
	// log.Printf("[sieve][NotifyStaleStateAfterSideEffects] %s %v\n", sideEffectType, object)
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
	request := &NotifyStaleStateAfterSideEffectsRequest{
		SideEffectID:   sideEffectID,
		SideEffectType: sideEffectType,
		Object:         string(jsonObject),
		ResourceType:   regularizeType(object),
		Error:          errorString,
	}
	var response Response
	err = client.Call("StaleStateListener.NotifyStaleStateAfterSideEffects", request, &response)
	if err != nil {
		printError(err, SIEVE_REPLY_ERR)
		return
	}
	checkResponse(response, "NotifyStaleStateAfterSideEffects")
	client.Close()
}
