package sonar

import (
	"log"
	"encoding/json"
	"reflect"
	"strings"
	"k8s.io/apimachinery/pkg/api/meta"
)

func isCRD(rType string, crds []string) bool {
	for _, crd := range crds {
		if rType == crd {
			return true
		}
	}
	return false
}

func triggerReconcile(object interface{}) bool {
	crds := getCRDs()
	rType := regularizeType(reflect.TypeOf(object).String())
	if isCRD(rType, crds) {
		return true
	}
	if o, err := meta.Accessor(object); err == nil {
		for _, ref := range o.GetOwnerReferences() {
			if isCRD(strings.ToLower(ref.Kind), crds) {
				taintMap.Store(o.GetNamespace() + "-" + rType + "-" + o.GetName(), "")
				return true
			} else if _, ok := taintMap.Load(o.GetNamespace() + "-" + strings.ToLower(ref.Kind) + "-" + ref.Name); ok {
				taintMap.Store(o.GetNamespace() + "-" + rType + "-" + o.GetName(), "")
				return true
			}
		}
	}
	return false
}

func NotifyLearnBeforeIndexerWrite(operationType string, object interface{}) {
	if !checkMode(learn) {
		return
	}
	if !triggerReconcile(object) {
		return
	}
	log.Printf("[sonar][NotifyLearnBeforeIndexerWrite] operationType: %s\n", operationType)
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, jsonError)
		return
	}
	request := &NotifyLearnBeforeIndexerWriteRequest{
		OperationType: operationType,
		Object: string(jsonObject),
		ResourceType: regularizeType(reflect.TypeOf(object).String()),
	}
	var response Response
	err = client.Call("LearnListener.NotifyLearnBeforeIndexerWrite", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyLearnBeforeIndexerWrite")
	client.Close()
}

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
	err = client.Call("LearnListener.NotifyLearnBeforeReconcile", request, &response)
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
	err = client.Call("LearnListener.NotifyLearnAfterReconcile", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyLearnAfterReconcile")
	client.Close()
}

func NotifyLearnSideEffects(sideEffectType string, object interface{}) {
	if !checkMode(learn) {
		return
	}
	log.Printf("[sonar][NotifyLearnSideEffects] %v\n", reflect.TypeOf(object))
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printError(err, jsonError)
	}
	client, err := newClient()
	if err != nil {
		printError(err, connectionError)
		return
	}
	request := &NotifyLearnSideEffectsRequest{
		SideEffectType: sideEffectType,
		Object: string(jsonObject),
		ResourceType: regularizeType(reflect.TypeOf(object).String()),
	}
	var response Response
	err = client.Call("LearnListener.NotifyLearnSideEffects", request, &response)
	if err != nil {
		printError(err, replyError)
		return
	}
	checkResponse(response, "NotifyLearnSideEffects")
	client.Close()
}
