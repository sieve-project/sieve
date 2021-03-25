package sonar

import (
	"encoding/json"
	"log"
	"os"
	"strings"
	"reflect"
)

func NotifyTimeTravelAfterProcessEvent(eventType, key string, object interface{}) {
	if !checkMode(timeTravel) {
		return
	}
	tokens := strings.Split(key, "/")
	name := ""
	namespace := ""
	resourceType := ""
	if len(tokens) == 4 {
		resourceType = tokens[1]
		namespace = tokens[2]
		name = tokens[3]
	} else if len(tokens) == 5 {
		resourceType = tokens[2]
		namespace = tokens[3]
		name = tokens[4]
	} else {
		return
	}
	if name == config["ce-name"].(string) && namespace == config["ce-namespace"].(string) && resourceType == config["ce-rtype"].(string) {
		log.Printf("[sonar][rt-ns-name] %s %s %s", resourceType, namespace, name)
		jsonObject, err := json.Marshal(object)
		if err != nil {
			printError(err, jsonError)
		}
		client, err := newClient()
		if err != nil {
			printError(err, connectionError)
			return
		}
		hostname, err := os.Hostname()
		if err != nil {
			printError(err, hostError)
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
			printError(err, replyError)
			return
		}
		checkResponse(response, "NotifyTimeTravelCrucialEvent")
		client.Close()
	} else if name == config["se-name"].(string) && namespace == config["se-namespace"].(string) && resourceType == config["se-rtype"].(string) && eventType == config["se-etype"] {
		log.Printf("[sonar][rt-ns-name] %s %s %s", resourceType, namespace, name)
		client, err := newClient()
		if err != nil {
			printError(err, connectionError)
			return
		}
		hostname, err := os.Hostname()
		if err != nil {
			printError(err, hostError)
			return
		}
		request := &NotifyTimeTravelSideEffectRequest{
			Hostname:     hostname,
			EventType:    eventType,
			ResourceType: resourceType,
			Name:         name,
			Namespace:    namespace,
		}
		var response Response
		err = client.Call("TimeTravelListener.NotifyTimeTravelSideEffect", request, &response)
		if err != nil {
			printError(err, replyError)
			return
		}
		checkResponse(response, "NotifyTimeTravelSideEffect")
		client.Close()
	}
}

func NotifyTimeTravelSideEffects(sideEffectType string, object interface{}) {
	if !checkMode(timeTravel) {
		return
	}
	log.Printf("[SONAR-SIDE-EFFECT]\t%s\t%s\n", sideEffectType, regularizeType(reflect.TypeOf(object).String()))
}
