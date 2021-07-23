package sonar

import (
	"encoding/json"
	"reflect"
	"runtime/debug"
)

func NotifyAtomicSideEffects(sideEffectType string, object interface{}) {
	if !checkStage(test) || !checkMode(modeAtomic) {
		return
	}
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
	request := &NotifyAtomicSideEffectsRequest{
		SideEffectType: sideEffectType,
		Object:         string(jsonObject),
		ResourceType:   regularizeType(reflect.TypeOf(object).String()),
		Error:          errorString,
		Stack:          string(debug.Stack()),
	}
	var response Response
	err = client.Call("AtomicListener.NotifyAtomicSideEffects", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyAtomicSideEffects")
	client.Close()
}
