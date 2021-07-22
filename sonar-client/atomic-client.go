package sonar

import (
	"encoding/json"
	"reflect"

	"k8s.io/apimachinery/pkg/api/errors"
)

func NotifyAtomicSideEffects(sideEffectType string, object interface{}, k8sErr error) {
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
	if k8sErr != nil {
		errorString = string(errors.ReasonForError(k8sErr))
	}
	request := &NotifyAtomicSideEffectsRequest{
		SideEffectType: sideEffectType,
		Object:         string(jsonObject),
		ResourceType:   regularizeType(reflect.TypeOf(object).String()),
		Error:          errorString,
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
