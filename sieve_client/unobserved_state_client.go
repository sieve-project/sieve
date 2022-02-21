package sieve

// func NotifyUnobsrStateBeforeIndexerWrite(operationType string, object interface{}) {
// 	if err := loadSieveConfig(); err != nil {
// 		return
// 	}
// 	// if !checkStage(TEST) || !checkMode(UNOBSERVED_STATE) {
// 	// 	return
// 	// }
// 	// rType := regularizeType(object)
// 	// if rType != config["ce-rtype"].(string) {
// 	// 	return
// 	// }
// 	// if !isSameObjectClientSide(object, config["ce-namespace"].(string), config["ce-name"].(string)) {
// 	// 	return
// 	// }
// 	// client, err := newClient()
// 	// if err != nil {
// 	// 	printError(err, SIEVE_CONN_ERR)
// 	// 	return
// 	// }
// 	// jsonObject, err := json.Marshal(object)
// 	// if err != nil {
// 	// 	printError(err, SIEVE_JSON_ERR)
// 	// 	return
// 	// }
// 	// log.Printf("[sieve][NotifyUnobsrStateBeforeIndexerWrite] type: %s object: %s\n", operationType, string(jsonObject))
// 	// request := &NotifyUnobsrStateBeforeIndexerWriteRequest{
// 	// 	OperationType: operationType,
// 	// 	Object:        string(jsonObject),
// 	// 	ResourceType:  rType,
// 	// }
// 	// var response Response
// 	// err = client.Call("UnobsrStateListener.NotifyUnobsrStateBeforeIndexerWrite", request, &response)
// 	// if err != nil {
// 	// 	printError(err, SIEVE_REPLY_ERR)
// 	// 	return
// 	// }
// 	// checkResponse(response, "NotifyUnobsrStateBeforeIndexerWrite")
// 	// client.Close()
// }

// func NotifyUnobsrStateAfterIndexerWrite(operationType string, object interface{}) {
// 	if err := loadSieveConfig(); err != nil {
// 		return
// 	}
// 	// if !checkStage(TEST) || !checkMode(UNOBSERVED_STATE) {
// 	// 	return
// 	// }
// 	// rType := regularizeType(object)
// 	// if rType != config["ce-rtype"].(string) {
// 	// 	return
// 	// }
// 	// if !isSameObjectClientSide(object, config["ce-namespace"].(string), config["ce-name"].(string)) {
// 	// 	return
// 	// }
// 	// client, err := newClient()
// 	// if err != nil {
// 	// 	printError(err, SIEVE_CONN_ERR)
// 	// 	return
// 	// }
// 	// jsonObject, err := json.Marshal(object)
// 	// if err != nil {
// 	// 	printError(err, SIEVE_JSON_ERR)
// 	// 	return
// 	// }
// 	// log.Printf("[sieve][NotifyUnobsrStateAfterIndexerWrite] type: %s object: %s\n", operationType, string(jsonObject))
// 	// request := &NotifyUnobsrStateAfterIndexerWriteRequest{
// 	// 	OperationType: operationType,
// 	// 	Object:        string(jsonObject),
// 	// 	ResourceType:  rType,
// 	// }
// 	// var response Response
// 	// err = client.Call("UnobsrStateListener.NotifyUnobsrStateAfterIndexerWrite", request, &response)
// 	// if err != nil {
// 	// 	printError(err, SIEVE_REPLY_ERR)
// 	// 	return
// 	// }
// 	// checkResponse(response, "NotifyUnobsrStateAfterIndexerWrite")
// 	// client.Close()
// }

// func NotifyUnobsrStateBeforeInformerCacheGet(readType string, namespacedName types.NamespacedName, object interface{}) {
// 	if err := loadSieveConfig(); err != nil {
// 		return
// 	}
// 	// if !checkStage(TEST) || !checkMode(UNOBSERVED_STATE) {
// 	// 	return
// 	// }
// 	// rType := regularizeType(object)
// 	// if rType != config["ce-rtype"].(string) {
// 	// 	return
// 	// }
// 	// if namespacedName.Name != config["ce-name"].(string) || namespacedName.Namespace != config["ce-namespace"].(string) {
// 	// 	return
// 	// }
// 	// log.Printf("[sieve][NotifyUnobsrStateBeforeInformerCacheGet] type: %s, ns: %s name: %s", rType, namespacedName.Namespace, namespacedName.Name)
// 	// client, err := newClient()
// 	// if err != nil {
// 	// 	printError(err, SIEVE_CONN_ERR)
// 	// 	return
// 	// }
// 	// request := &NotifyUnobsrStateBeforeInformerCacheReadRequest{
// 	// 	OperationType: readType,
// 	// 	ResourceType:  rType,
// 	// 	Namespace:     namespacedName.Namespace,
// 	// 	Name:          namespacedName.Name,
// 	// }
// 	// var response Response
// 	// err = client.Call("UnobsrStateListener.NotifyUnobsrStateBeforeInformerCacheRead", request, &response)
// 	// if err != nil {
// 	// 	printError(err, SIEVE_REPLY_ERR)
// 	// 	return
// 	// }
// 	// checkResponse(response, "NotifyUnobsrStateBeforeInformerCacheGet")
// 	// client.Close()
// }

// func NotifyUnobsrStateAfterInformerCacheGet(readType string, namespacedName types.NamespacedName, object interface{}) {
// 	if err := loadSieveConfig(); err != nil {
// 		return
// 	}
// 	// if !checkStage(TEST) || !checkMode(UNOBSERVED_STATE) {
// 	// 	return
// 	// }
// 	// rType := regularizeType(object)
// 	// if rType != config["ce-rtype"].(string) {
// 	// 	return
// 	// }
// 	// if namespacedName.Name != config["ce-name"].(string) || namespacedName.Namespace != config["ce-namespace"].(string) {
// 	// 	return
// 	// }
// 	// log.Printf("[sieve][NotifyUnobsrStateAfterInformerCacheGet] type: %s, ns: %s name: %s", rType, namespacedName.Namespace, namespacedName.Name)
// 	// client, err := newClient()
// 	// if err != nil {
// 	// 	printError(err, SIEVE_CONN_ERR)
// 	// 	return
// 	// }
// 	// request := &NotifyUnobsrStateAfterInformerCacheReadRequest{
// 	// 	OperationType: readType,
// 	// 	ResourceType:  rType,
// 	// 	Namespace:     namespacedName.Namespace,
// 	// 	Name:          namespacedName.Name,
// 	// }
// 	// var response Response
// 	// err = client.Call("UnobsrStateListener.NotifyUnobsrStateAfterInformerCacheRead", request, &response)
// 	// if err != nil {
// 	// 	printError(err, SIEVE_REPLY_ERR)
// 	// 	return
// 	// }
// 	// checkResponse(response, "NotifyUnobsrStateAfterInformerCacheGet")
// 	// client.Close()
// }

// func NotifyUnobsrStateBeforeInformerCacheList(readType string, object interface{}) {
// 	if err := loadSieveConfig(); err != nil {
// 		return
// 	}
// 	// if !checkStage(TEST) || !checkMode(UNOBSERVED_STATE) {
// 	// 	return
// 	// }
// 	// rType := regularizeType(object)
// 	// if rType != config["ce-rtype"].(string)+"list" {
// 	// 	return
// 	// }
// 	// log.Printf("[sieve][NotifyUnobsrStateBeforeInformerCacheList] type: %s", rType)
// 	// client, err := newClient()
// 	// if err != nil {
// 	// 	printError(err, SIEVE_CONN_ERR)
// 	// 	return
// 	// }
// 	// request := &NotifyUnobsrStateBeforeInformerCacheReadRequest{
// 	// 	OperationType: readType,
// 	// 	ResourceType:  rType,
// 	// }
// 	// var response Response
// 	// err = client.Call("UnobsrStateListener.NotifyUnobsrStateBeforeInformerCacheRead", request, &response)
// 	// if err != nil {
// 	// 	printError(err, SIEVE_REPLY_ERR)
// 	// 	return
// 	// }
// 	// checkResponse(response, "NotifyUnobsrStateBeforeInformerCacheList")
// 	// client.Close()
// }

// func NotifyUnobsrStateAfterInformerCacheList(readType string, object interface{}) {
// 	if err := loadSieveConfig(); err != nil {
// 		return
// 	}
// 	// if !checkStage(TEST) || !checkMode(UNOBSERVED_STATE) {
// 	// 	return
// 	// }
// 	// rType := regularizeType(object)
// 	// if rType != config["ce-rtype"].(string)+"list" {
// 	// 	return
// 	// }
// 	// log.Printf("[sieve][NotifyUnobsrStateAfterInformerCacheList] type: %s", rType)
// 	// client, err := newClient()
// 	// if err != nil {
// 	// 	printError(err, SIEVE_CONN_ERR)
// 	// 	return
// 	// }
// 	// request := &NotifyUnobsrStateAfterInformerCacheReadRequest{
// 	// 	OperationType: readType,
// 	// 	ResourceType:  rType,
// 	// }
// 	// var response Response
// 	// err = client.Call("UnobsrStateListener.NotifyUnobsrStateAfterInformerCacheRead", request, &response)
// 	// if err != nil {
// 	// 	printError(err, SIEVE_REPLY_ERR)
// 	// 	return
// 	// }
// 	// checkResponse(response, "NotifyUnobsrStateAfterInformerCacheList")
// 	// client.Close()
// }
