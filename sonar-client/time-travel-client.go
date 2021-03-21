package sonar

import (
	"os"
	"time"
	"log"
	"encoding/json"
)

// NotifyTimeTravelBeforeProcessEvent is invoked before apiserver calling processEvent()
// NotifyTimeTravelBeforeProcessEvent lets the server know the apiserver is going to process an event from etcd,
// the server should decide whether to freeze the apiserver or restart the controller.
func NotifyTimeTravelBeforeProcessEvent(eventType, resourceType string, object interface{}) {
	if !checkMode(timeTravel) {
		return
	}
	if resourceType == config["freeze-resource-type"] && eventType == config["freeze-event-type"] {
		jsonObject, err := json.Marshal(object)
		if err != nil {
			printError(err, jsonError)
			return
		}
		jsonMap := make(map[string]interface{})
		err = json.Unmarshal(jsonObject, &jsonMap)
		if err != nil {
			printError(err, jsonError)
			return
		}
		log.Printf("[soanr][jsonmap] %v\n", jsonMap)
		ret := true
		if meta, ok := jsonMap["metadata"]; ok {
			if metaMap, ok := meta.(map[string]interface{}); ok {
				if name, ok := metaMap["name"]; ok {
					if nameStr, ok := name.(string); ok {
						if nameStr == config["freeze-resource-name"] {
							ret = false
						}
					}
				}	
			}
		} else if name, ok := jsonMap["name"]; ok {
			if nameStr, ok := name.(string); ok {
				if nameStr == config["freeze-resource-name"] {
					ret = false
				}
			}
		}
		if ret {
			return
		}
		log.Printf("[sonar][NotifyTimeTravelBeforeProcessEvent][freeze] eventType: %s, resourceType: %s\n", eventType, resourceType)
	} else if resourceType == config["restart-resource-type"] && eventType == config["restart-event-type"] {
		log.Printf("[sonar][NotifyTimeTravelBeforeProcessEvent][restart] eventType: %s, resourceType: %s\n", eventType, resourceType)
	} else {
		return
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
	request := &NotifyTimeTravelBeforeProcessEventRequest{
		EventType:    eventType,
		ResourceType: resourceType,
		Hostname:     hostname,
	}
	var response Response
	err = client.Call("TimeTravelListener.NotifyTimeTravelBeforeProcessEvent", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyTimeTravelBeforeProcessEvent")
	if response.Wait != 0 {
		log.Printf("[sonar][NotifyTimeTravelBeforeProcessEvent] should sleep for %d seconds here", response.Wait)
		time.Sleep(time.Duration(response.Wait) * time.Second)
	}
	client.Close()
}