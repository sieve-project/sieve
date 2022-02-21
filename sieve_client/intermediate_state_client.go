package sieve

// import (
// 	"k8s.io/apimachinery/pkg/types"
// )

// func NotifyIntmdStateAfterOperatorGet(readType string, fromCache bool, namespacedName types.NamespacedName, object interface{}, k8sErr error) {
// 	if err := loadSieveConfig(); err != nil {
// 		return
// 	}
// 	// if !checkStage(TEST) || !checkMode(INTERMEDIATE_STATE) {
// 	// 	return
// 	// }
// 	// reconcilerType := getReconcilerFromStackTrace()
// 	// if reconcilerType != config["se-reconciler-type"] {
// 	// 	return
// 	// }
// 	// rType := regularizeType(object)
// 	// if !(config["se-etype-previous"].(string) == "Get" && rType == config["se-rtype"].(string)) {
// 	// 	return
// 	// }
// 	// if !isSameObjectClientSide(object, config["se-namespace"].(string), config["se-name"].(string)) {
// 	// 	return
// 	// }
// 	// jsonObject, err := json.Marshal(object)
// 	// if err != nil {
// 	// 	printError(err, SIEVE_JSON_ERR)
// 	// 	return
// 	// }
// 	// client, err := newClient()
// 	// if err != nil {
// 	// 	printError(err, SIEVE_CONN_ERR)
// 	// 	return
// 	// }
// 	// defer client.Close()
// 	// errorString := "NoError"
// 	// if k8sErr != nil {
// 	// 	errorString = string(errors.ReasonForError(k8sErr))
// 	// }
// 	// request := &NotifyIntmdStateAfterOperatorGetRequest{
// 	// 	ResourceType:   regularizeType(object),
// 	// 	Namespace:      namespacedName.Namespace,
// 	// 	Name:           namespacedName.Name,
// 	// 	Object:         string(jsonObject),
// 	// 	ReconcilerType: reconcilerType,
// 	// 	Error:          errorString,
// 	// }
// 	// var response Response
// 	// err = client.Call("IntmdStateListener.NotifyIntmdStateAfterOperatorGet", request, &response)
// 	// if err != nil {
// 	// 	printError(err, SIEVE_REPLY_ERR)
// 	// 	return
// 	// }
// 	// checkResponse(response, "NotifyIntmdStateAfterOperatorGet")
// }

// func NotifyIntmdStateAfterOperatorList(readType string, fromCache bool, object interface{}, k8sErr error) {
// 	if err := loadSieveConfig(); err != nil {
// 		return
// 	}
// 	// if !checkStage(TEST) || !checkMode(INTERMEDIATE_STATE) {
// 	// 	return
// 	// }
// 	// reconcilerType := getReconcilerFromStackTrace()
// 	// if reconcilerType != config["se-reconciler-type"] {
// 	// 	return
// 	// }
// 	// rType := regularizeType(object)
// 	// if !(config["se-etype-previous"].(string) == "List" && rType == config["se-rtype"].(string)+"list") {
// 	// 	return
// 	// }
// 	// jsonObject, err := json.Marshal(object)
// 	// if err != nil {
// 	// 	printError(err, SIEVE_JSON_ERR)
// 	// 	return
// 	// }
// 	// client, err := newClient()
// 	// if err != nil {
// 	// 	printError(err, SIEVE_CONN_ERR)
// 	// 	return
// 	// }
// 	// defer client.Close()
// 	// errorString := "NoError"
// 	// if k8sErr != nil {
// 	// 	errorString = string(errors.ReasonForError(k8sErr))
// 	// }
// 	// request := &NotifyIntmdStateAfterOperatorListRequest{
// 	// 	ResourceType:   rType,
// 	// 	ObjectList:     string(jsonObject),
// 	// 	ReconcilerType: reconcilerType,
// 	// 	Error:          errorString,
// 	// }
// 	// var response Response
// 	// err = client.Call("IntmdStateListener.NotifyIntmdStateAfterOperatorList", request, &response)
// 	// if err != nil {
// 	// 	printError(err, SIEVE_REPLY_ERR)
// 	// 	return
// 	// }
// 	// checkResponse(response, "NotifyIntmdStateAfterOperatorList")
// }

// func NotifyIntmdStateAfterSideEffects(sideEffectID int, sideEffectType string, object interface{}, k8sErr error) {
// 	if err := loadSieveConfig(); err != nil {
// 		return
// 	}
// 	// if !checkStage(TEST) || !checkMode(INTERMEDIATE_STATE) {
// 	// 	return
// 	// }
// 	// reconcilerType := getReconcilerFromStackTrace()
// 	// if reconcilerType != config["se-reconciler-type"] {
// 	// 	return
// 	// }
// 	// errorString := "NoError"
// 	// if k8sErr != nil {
// 	// 	errorString = string(errors.ReasonForError(k8sErr))
// 	// }
// 	// rType := regularizeType(object)
// 	// if !(rType == config["se-rtype"].(string) && errorString == "NoError") {
// 	// 	return
// 	// }
// 	// if !isSameObjectClientSide(object, config["se-namespace"].(string), config["se-name"].(string)) {
// 	// 	return
// 	// }
// 	// jsonObject, err := json.Marshal(object)
// 	// if err != nil {
// 	// 	printError(err, SIEVE_JSON_ERR)
// 	// 	return
// 	// }
// 	// client, err := newClient()
// 	// if err != nil {
// 	// 	printError(err, SIEVE_CONN_ERR)
// 	// 	return
// 	// }
// 	// defer client.Close()
// 	// request := &NotifyIntmdStateAfterSideEffectsRequest{
// 	// 	SideEffectID:   sideEffectID,
// 	// 	SideEffectType: sideEffectType,
// 	// 	Object:         string(jsonObject),
// 	// 	ResourceType:   rType,
// 	// 	ReconcilerType: reconcilerType,
// 	// 	Error:          errorString,
// 	// }
// 	// var response Response
// 	// err = client.Call("IntmdStateListener.NotifyIntmdStateAfterSideEffects", request, &response)
// 	// if err != nil {
// 	// 	printError(err, SIEVE_REPLY_ERR)
// 	// 	return
// 	// }
// 	// checkResponse(response, "NotifyIntmdStateAfterSideEffects")
// }

// func NotifyIntmdStateAfterNonK8sSideEffects(sideEffectID int, typeName, funName string) {
// 	if err := loadSieveConfig(); err != nil {
// 		return
// 	}
// 	// if !checkStage(TEST) || !checkMode(INTERMEDIATE_STATE) {
// 	// 	return
// 	// }
// 	// reconcilerType := getReconcilerFromStackTrace()
// 	// if reconcilerType == "" {
// 	// 	reconcilerType = UNKNOWN_RECONCILER_TYPE
// 	// }
// 	// client, err := newClient()
// 	// if err != nil {
// 	// 	printError(err, SIEVE_CONN_ERR)
// 	// 	return
// 	// }
// 	// request := &NotifyIntmdStateAfterNonK8sSideEffectsRequest{
// 	// 	SideEffectID:   sideEffectID,
// 	// 	RecvTypeName:   typeName,
// 	// 	FunName:        funName,
// 	// 	ReconcilerType: reconcilerType,
// 	// }
// 	// var response Response
// 	// err = client.Call("IntmdStateListener.NotifyIntmdStateAfterNonK8sSideEffects", request, &response)
// 	// if err != nil {
// 	// 	printError(err, SIEVE_REPLY_ERR)
// 	// 	return
// 	// }
// 	// checkResponse(response, "NotifyIntmdStateAfterNonK8sSideEffects")
// 	// client.Close()
// }

// func NotifyIntmdStateBeforeProcessEvent(eventType, key string, object interface{}) {
// 	loadSieveConfigFromConfigMap(eventType, key, object)
// 	// if err := loadSieveConfig(); err != nil {
// 	// 	return
// 	// }
// 	// tokens := strings.Split(key, "/")
// 	// namespace := tokens[len(tokens)-2]
// 	// if namespace == config["se-namespace"].(string) {
// 	// 	if !checkStage(TEST) || !checkMode(INTERMEDIATE_STATE) {
// 	// 		return
// 	// 	}
// 	// 	jsonObject, err := json.Marshal(object)
// 	// 	if err != nil {
// 	// 		printError(err, SIEVE_JSON_ERR)
// 	// 		return
// 	// 	}
// 	// 	if len(tokens) < 4 {
// 	// 		log.Printf("unrecognizable key %s\n", key)
// 	// 		return
// 	// 	}
// 	// 	resourceType := regularizeType(object)
// 	// 	namespace := tokens[len(tokens)-2]
// 	// 	name := tokens[len(tokens)-1]
// 	// 	log.Printf("[SIEVE-API-EVENT]\t%s\t%s\t%s\t%s\t%s\t%s\n", eventType, key, resourceType, namespace, name, string(jsonObject))
// 	// }
// }
