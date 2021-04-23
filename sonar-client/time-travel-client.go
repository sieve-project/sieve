package sonar

import (
	"encoding/json"
	"log"
	"os"
	"strings"
	"reflect"

	"k8s.io/apimachinery/pkg/api/errors"
	// "k8s.io/apimachinery/pkg/api/meta"
)

func NotifyTimeTravelAfterProcessEvent(eventType, key string, object interface{}) {
	if checkTimeTravelTiming("after") {
		log.Printf("[sonar] NotifyTimeTravelAfterProcessEvent")
		NotifyTimeTravelAboutProcessEvent(eventType, key, object)
	}
}

func NotifyTimeTravelBeforeProcessEvent(eventType, key string, object interface{}) {
	if checkTimeTravelTiming("before") {
		log.Printf("[sonar] NotifyTimeTravelBeforeProcessEvent")
		NotifyTimeTravelAboutProcessEvent(eventType, key, object)
	}
}

func NotifyTimeTravelAboutProcessEvent(eventType, key string, object interface{}) {
	tokens := strings.Split(key, "/")
	if len(tokens) < 4 {
		return
	}
	resourceType := pluralToSingle(tokens[len(tokens) - 3])
	namespace := tokens[len(tokens) - 2]
	name := tokens[len(tokens) - 1]
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
			printError(err, replyError)
			return
		}
		checkResponse(response, "NotifyTimeTravelRestartPoint")
		client.Close()
	}
}

// func extractNameNamespaceFromObj(object interface{}) (string, string) {
// 	name := "unknown"
// 	namespace := "unknown"
// 	if o, err := meta.Accessor(object); err == nil {
// 		return o.GetName(), o.GetNamespace()
// 	}
// 	return name, namespace
// }

func NotifyTimeTravelSideEffects(sideEffectType string, object interface{}, k8sErr error) {
	if !checkMode(timeTravel) {
		return
	}
	log.Printf("[sonar][NotifyTimeTravelSideEffects] %s %v\n", sideEffectType, object)
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, jsonError)
	}
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	errorString := "NoError"
	if k8sErr != nil {
		errorString = string(errors.ReasonForError(k8sErr))
	}
	request := &NotifyTimeTravelSideEffectsRequest{
		SideEffectType: sideEffectType,
		Object: string(jsonObject),
		ResourceType: regularizeType(reflect.TypeOf(object).String()),
		Error: errorString,
	}
	var response Response
	err = client.Call("TimeTravelListener.NotifyTimeTravelSideEffects", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyTimeTravelSideEffects")
	client.Close()
}
