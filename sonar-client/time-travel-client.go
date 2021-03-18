package sonar

import (
	"os"
	"time"
	"log"
)

// NotifyTimeTravelBeforeProcessEvent is invoked before apiserver calling processEvent()
// NotifyTimeTravelBeforeProcessEvent lets the server know the apiserver is going to process an event from etcd,
// the server should decide whether to freeze the apiserver or restart the controller.
func NotifyTimeTravelBeforeProcessEvent(eventType, resourceType string) {
	if !checkMode(timeTravel) {
		// log.Printf("[sonar][NOT-ready][NotifyTimeTravelBeforeProcessEvent] eventType: %s, resourceType: %s\n", eventType, resourceType)
		return
	}
	log.Printf("[sonar][test][NotifyTimeTravelBeforeProcessEvent] eventType: %s, resourceType: %s\n", eventType, resourceType)
	if resourceType != config["freeze-resource-type"] && resourceType != config["restart-resource-type"] {
		return
	}
	log.Printf("[sonar][NotifyTimeTravelBeforeProcessEvent] eventType: %s, resourceType: %s\n", eventType, resourceType)
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