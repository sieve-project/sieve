package sonar

import (
	"log"
)

func NotifyLearnBeforeReconcile() {
	if !checkMode(learn) {
		return
	}
	log.Printf("[sonar][NotifyLearnBeforeReconcile]\n")
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	request := &NotifyLearnBeforeReconcileRequest{
		Nothing: "nothing",
	}
	var response Response
	err = client.Call("LearnListener.NotifyBeforeReconcile", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyLearnBeforeReconcile")
	client.Close()
}

func NotifyLearnAfterReconcile() {
	if !checkMode(learn) {
		return
	}
	log.Printf("[sonar][NotifyLearnAfterReconcile]\n")
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	request := &NotifyLearnAfterReconcileRequest{
		Nothing: "nothing",
	}
	var response Response
	err = client.Call("LearnListener.NotifyAfterReconcile", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyLearnAfterReconcile")
	client.Close()
}

func NotifyLearnSideEffects(sideEffectType string) {
	if !checkMode(learn) {
		return
	}
	log.Printf("[sonar][NotifyLearnSideEffects]\n")
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	request := &NotifyLearnSideEffectsRequest{
		SideEffectType: sideEffectType,
	}
	var response Response
	err = client.Call("LearnListener.NotifySideEffects", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyLearnSideEffects")
	client.Close()
}
