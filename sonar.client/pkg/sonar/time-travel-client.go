package sonar

import (
	"os"
	"time"
	"log"
)

// NotifyBeforeProcessEvent is invoked before apiserver calling processEvent()
// NotifyBeforeProcessEvent lets the server know the apiserver is going to process an event from etcd,
// the server should decide whether to freeze the apiserver or restart the controller.
func NotifyBeforeProcessEvent(eventType, resourceType string) {
	if !checkMode(timeTravel) {
		// log.Printf("[sonar][NOT-ready][NotifyBeforeProcessEvent] eventType: %s, resourceType: %s\n", eventType, resourceType)
		return
	}
	log.Printf("[sonar][test][NotifyBeforeProcessEvent] eventType: %s, resourceType: %s\n", eventType, resourceType)
	if resourceType != config["freeze-resource-type"] && resourceType != config["restart-resource-type"] {
		return
	}
	log.Printf("[sonar][NotifyBeforeProcessEvent] eventType: %s, resourceType: %s\n", eventType, resourceType)
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
	request := &NotifyBeforeProcessEventRequest{
		EventType:    eventType,
		ResourceType: resourceType,
		Hostname:     hostname,
	}
	var response Response
	err = client.Call("TimeTravelListener.NotifyBeforeProcessEvent", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyBeforeProcessEvent")
	if response.Wait != 0 {
		log.Printf("[sonar][NotifyBeforeProcessEvent] should sleep for %d seconds here", response.Wait)
		time.Sleep(time.Duration(response.Wait) * time.Second)
	}
	client.Close()
}