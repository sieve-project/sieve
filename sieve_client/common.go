package sieve

import (
	"encoding/json"
	"fmt"
	"log"
	"net/rpc"
	"os"
	"path"
	"reflect"
	"runtime/debug"
	"strings"
	"sync"

	"gopkg.in/yaml.v2"
	"k8s.io/apimachinery/pkg/api/meta"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
)

const LEARN string = "learn"
const TEST string = "test"
const UNKNOWN_RECONCILER_TYPE = "Unknown"

// TODO(xudong): make SIEVE_SERVER_ADDR configurable
const SIEVE_SERVER_ADDR string = "kind-control-plane:12345"

const HTTP_GET string = "GET"
const HTTP_POST string = "POST"
const HTTP_PUT string = "PUT"
const HTTP_PATCH string = "PATCH"
const HTTP_DELETE string = "DELETE"

const GET string = "Get"
const LIST string = "List"
const CREATE string = "Create"
const UPDATE string = "Update"
const STATUSUPDATE string = "StatusUpdate"
const PATCH string = "Patch"
const DELETE string = "Delete"
const DELETEALLOF string = "DeleteAllOf"

const UNKNOWN string = "Unknown"

const NO_ERROR string = "NoError"

var config map[string]interface{} = nil
var configLoadingLock sync.Mutex
var triggerDefinitionsByResourceKey map[string][]map[interface{}]interface{} = make(map[string][]map[interface{}]interface{})
var triggerDefinitionsByAnnotatedAPI map[string][]map[interface{}]interface{} = make(map[string][]map[interface{}]interface{})
var actions map[string][]map[interface{}]interface{} = make(map[string][]map[interface{}]interface{})
var apiserverHostname string = ""
var rpcClient *rpc.Client = nil

var exists = struct{}{}
var taintMap sync.Map = sync.Map{}

func printSerializationError(err error) {
	log.Printf("Sieve client serialization error: %v\n", err)
}

func printRPCError(err error) {
	log.Printf("Sieve client RPC error: %v\n", err)
}

func printConfigError(err error) {
	log.Printf("Sieve client configuration error: %v\n", err)
}

func HttpVerbToControllerOperation(verb, resourceName, subresource string) string {
	switch verb {
	case HTTP_GET:
		if resourceName == "" {
			return LIST
		} else {
			return GET
		}
	case HTTP_POST:
		return CREATE
	case HTTP_PUT:
		if subresource == "status" {
			return STATUSUPDATE
		} else {
			return UPDATE
		}
	case HTTP_PATCH:
		return PATCH
	case HTTP_DELETE:
		if resourceName == "" {
			return DELETEALLOF
		} else {
			return DELETE
		}
	default:
		return UNKNOWN
	}
}

func checkKVPairInAction(actionType, key, val string, matchPrefix bool) bool {
	for actionKey, actionsOfTheSameType := range actions {
		if actionKey == actionType {
			for _, action := range actionsOfTheSameType {
				if valInTestPlan, ok := action[key]; ok {
					if valInTestPlanStr, ok := valInTestPlan.(string); ok {
						if val == valInTestPlanStr {
							return true
						}
						if matchPrefix && strings.HasPrefix(valInTestPlanStr, val) {
							return true
						}
					}
				}
			}
		}
	}
	return false
}

func checkKVPairInAnnotatedAPICallTriggerCondition(apiKey string) bool {
	if _, ok := triggerDefinitionsByAnnotatedAPI[apiKey]; ok {
		return true
	} else {
		return false
	}
}

func checkKVPairInTriggerContent(content map[interface{}]interface{}, key, val string) bool {
	if valInTestPlan, ok := content[key]; ok {
		if valInTestPlanStr, ok := valInTestPlan.(string); ok {
			if val == valInTestPlanStr {
				return true
			}
		}
	}
	return false
}

func checkKVPairInTriggerCondition(resourceKey, key, val string, onlyMatchType bool) bool {
	for triggerResourceKey, triggers := range triggerDefinitionsByResourceKey {
		if triggerResourceKey == resourceKey || (onlyMatchType && strings.HasPrefix(triggerResourceKey, resourceKey+"/")) {
			for _, trigger := range triggers {
				if triggerCondition, ok := trigger["condition"]; ok {
					if triggerConditionMap, ok := triggerCondition.(map[interface{}]interface{}); ok {
						if checkKVPairInTriggerContent(triggerConditionMap, key, val) {
							return true
						}
					}
				}
			}
		}
	}
	return false
}

func checkKVPairInTriggerObservationPoint(resourceKey, key, val string, onlyMatchType bool) bool {
	for triggerResourceKey, triggers := range triggerDefinitionsByResourceKey {
		if triggerResourceKey == resourceKey || (onlyMatchType && strings.HasPrefix(triggerResourceKey, resourceKey+"/")) {
			for _, trigger := range triggers {
				if triggerObservationPoint, ok := trigger["observationPoint"]; ok {
					if triggerObservationPointMap, ok := triggerObservationPoint.(map[interface{}]interface{}); ok {
						if checkKVPairInTriggerContent(triggerObservationPointMap, key, val) {
							return true
						}
					}
				}
			}
		}
	}
	return false
}

func loadTriggerDefinitions(trigger map[interface{}]interface{}) error {
	definitions, ok := trigger["definitions"].([]interface{})
	if !ok {
		return fmt.Errorf("cannot convert trigger[\"definitions\"] to []interface{}")
	}
	for idx, definitionRaw := range definitions {
		definition, ok := definitionRaw.(map[interface{}]interface{})
		if !ok {
			return fmt.Errorf("cannot convert trigger[\"definitions\"][%d] to map[interface{}]interface{}", idx)
		}
		conditionRaw, ok := definition["condition"]
		if !ok {
			return fmt.Errorf("cannot find condition in trigger[\"definitions\"][%d]", idx)
		}
		condition, ok := conditionRaw.(map[interface{}]interface{})
		if !ok {
			return fmt.Errorf("cannot convert trigger[\"definitions\"][%d][\"condition\"] to map[interface{}]interface{}", idx)
		}
		conditionTypeRaw, ok := condition["conditionType"]
		if !ok {
			return fmt.Errorf("cannot find conditionType in trigger[\"definitions\"][%d][\"condition\"]", idx)
		}
		conditionType, ok := conditionTypeRaw.(string)
		if !ok {
			return fmt.Errorf("cannot convert trigger[\"definitions\"][%d][\"condition\"] to string", idx)
		}
		if conditionType == "onTimeout" {
			continue
		} else if conditionType == "onAnnotatedAPICall" {
			receiverTypeRaw, ok := condition["receiverType"]
			if !ok {
				return fmt.Errorf("cannot find receiverType in trigger[\"definitions\"][%d][\"condition\"]", idx)
			}
			receiverType, ok := receiverTypeRaw.(string)
			if !ok {
				return fmt.Errorf("cannot convert trigger[\"definitions\"][%d][\"condition\"][\"receiverType\"] to string", idx)
			}
			funNameRaw, ok := condition["funName"]
			if !ok {
				return fmt.Errorf("cannot find funName in trigger[\"definitions\"][%d][\"condition\"]", idx)
			}
			funName, ok := funNameRaw.(string)
			if !ok {
				return fmt.Errorf("cannot convert trigger[\"definitions\"][%d][\"condition\"][\"funName\"] to string", idx)
			}
			apiKey := receiverType + funName
			if _, ok := triggerDefinitionsByAnnotatedAPI[apiKey]; !ok {
				triggerDefinitionsByAnnotatedAPI[apiKey] = []map[interface{}]interface{}{}
			}
			triggerDefinitionsByAnnotatedAPI[apiKey] = append(triggerDefinitionsByAnnotatedAPI[apiKey], definition)
		} else {
			resourceKeyRaw, ok := condition["resourceKey"]
			if !ok {
				return fmt.Errorf("cannot find resourceKey in trigger[\"definitions\"][%d][\"condition\"]", idx)
			}
			resourceKey, ok := resourceKeyRaw.(string)
			if !ok {
				return fmt.Errorf("cannot convert trigger[\"definitions\"][%d][\"condition\"][\"resourceKey\"] to string", idx)
			}
			if _, ok := triggerDefinitionsByResourceKey[resourceKey]; !ok {
				triggerDefinitionsByResourceKey[resourceKey] = []map[interface{}]interface{}{}
			}
			triggerDefinitionsByResourceKey[resourceKey] = append(triggerDefinitionsByResourceKey[resourceKey], definition)
		}
	}
	return nil
}

func loadActions(action map[interface{}]interface{}) error {
	actionType, ok := action["actionType"].(string)
	if !ok {
		return fmt.Errorf("cannot convert action[\"actionType\"] to string")
	}
	if _, ok := actions[actionType]; !ok {
		actions[actionType] = []map[interface{}]interface{}{}
	}
	actions[actionType] = append(actions[actionType], action)
	return nil
}

func loadActionsAndTriggers(testPlan map[string]interface{}) error {
	actions, ok := testPlan["actions"].([]interface{})
	if !ok {
		return fmt.Errorf("cannot convert testPlan[\"actions\"] to []interface{}")
	}
	for idx, val := range actions {
		action, ok := val.(map[interface{}]interface{})
		err := loadActions(action)
		if err != nil {
			return nil
		}
		if !ok {
			return fmt.Errorf("cannot convert testPlan[\"actions\"][%d] to []interface{}", idx)
		}
		trigger, ok := action["trigger"].(map[interface{}]interface{})
		if !ok {
			return fmt.Errorf("cannot convert testPlan[\"actions\"][%d][\"trigger\"] to []interface{}", idx)
		}
		err = loadTriggerDefinitions(trigger)
		if err != nil {
			return err
		}
	}
	log.Printf("triggerDefinitionsByResourceKey:\n%v\n", triggerDefinitionsByResourceKey)
	return nil
}

func loadSieveConfigFromEnv(testMode bool) error {
	if config != nil {
		return nil
	}
	configLoadingLock.Lock()
	defer configLoadingLock.Unlock()
	if config != nil {
		return nil
	}
	if _, ok := os.LookupEnv("sieveTestPlan"); ok {
		configFromEnv := make(map[string]interface{})
		data := os.Getenv("sieveTestPlan")
		err := yaml.Unmarshal([]byte(data), &configFromEnv)
		if err != nil {
			printSerializationError(err)
			return fmt.Errorf("fail to load from env")
		}
		log.Printf("config from env:\n%v\n", configFromEnv)
		config = configFromEnv
		if testMode {
			err = loadActionsAndTriggers(configFromEnv)
			if err != nil {
				printConfigError(err)
				log.Println("failure in loadActionsAndTriggers")
				return nil
			}
		}
	} else {
		return fmt.Errorf("fail to load from env")
	}
	return nil
}

func loadSieveConfigFromConfigMap(eventType, key string, object interface{}, testMode bool) error {
	if config != nil {
		return nil
	}
	if eventType == "ADDED" {
		tokens := strings.Split(key, "/")
		if len(tokens) < 4 {
			return fmt.Errorf("tokens len should be >= 4")
		}
		namespace := tokens[len(tokens)-2]
		name := tokens[len(tokens)-1]
		if namespace == "default" && name == "sieve-testing-global-config" {
			resourceType := getResourceTypeFromObj(object)
			if resourceType == "configmap" {
				log.Println("have seen ADDED configmap/default/sieve-testing-global-config")
				jsonObject, err := json.Marshal(object)
				if err != nil {
					printSerializationError(err)
					return fmt.Errorf("fail to load from configmap")
				}
				configMapObject := make(map[string]interface{})
				err = yaml.Unmarshal(jsonObject, &configMapObject)
				if err != nil {
					printSerializationError(err)
					return fmt.Errorf("fail to load from configmap")
				}
				configFromConfigMapData := make(map[string]interface{})
				configMapData, ok := configMapObject["Data"].(map[interface{}]interface{})
				if !ok {
					log.Printf("cannot convert configMapObject[\"Data\"] to map[interface{}]interface{}")
					return fmt.Errorf("fail to load from configmap")
				}
				if str, ok := configMapData["sieveTestPlan"].(string); ok {
					err = yaml.Unmarshal([]byte(str), &configFromConfigMapData)
					if err != nil {
						printSerializationError(err)
						return fmt.Errorf("fail to load from configmap")
					}
					log.Printf("config from configMap:\n%v\n", configFromConfigMapData)
					config = configFromConfigMapData
					if testMode {
						err = loadActionsAndTriggers(configFromConfigMapData)
						if err != nil {
							printConfigError(err)
							log.Println("failure in loadActionsAndTriggers")
							return nil
						}
					}
				} else {
					log.Printf("cannot convert %v to string", configMapData["sieveTestPlan"])
					return fmt.Errorf("fail to load from configmap")
				}
			} else {
				return fmt.Errorf("have not seen ADDED configmap/default/sieve-testing-global-config yet")
			}
		} else {
			return fmt.Errorf("have not seen ADDED configmap/default/sieve-testing-global-config yet")
		}
	} else {
		return fmt.Errorf("have not seen ADDED configmap/default/sieve-testing-global-config yet")
	}
	return nil
}

func initAPIServerHostName() error {
	if apiserverHostname != "" {
		return nil
	}
	configLoadingLock.Lock()
	defer configLoadingLock.Unlock()
	if apiserverHostname != "" {
		return nil
	}
	var err error = nil
	apiserverHostname, err = os.Hostname()
	if err != nil {
		log.Printf("error in getting host name\n")
		return err
	}
	return nil
}

func initRPCClient() error {
	if rpcClient != nil {
		return nil
	}
	configLoadingLock.Lock()
	defer configLoadingLock.Unlock()
	if rpcClient != nil {
		return nil
	}
	var err error
	hostPort := SIEVE_SERVER_ADDR
	if val, ok := config["serverEndpoint"]; ok {
		hostPort = val.(string)
	}
	rpcClient, err = rpc.Dial("tcp", hostPort)
	if err != nil {
		log.Printf("error in setting up connection to %s due to %v\n", hostPort, err)
		return err
	}
	return nil
}

func getCRDs() []string {
	crds := []string{}
	if cs, ok := config["crdList"]; ok {
		switch v := cs.(type) {
		case []interface{}:
			for _, c := range v {
				crds = append(crds, c.(string))
			}
		case []string:
			for _, c := range v {
				crds = append(crds, c)
			}
		default:
			log.Println("crdList wrong type")
		}
	} else {
		log.Println("do not find crdList from config")
	}
	return crds
}

func checkResponse(response Response) {
	if !response.Ok {
		log.Printf("Sieve client receives bad response: %s\n", response.Message)
	}
}

func generateResourceKey(resourceType, namespace, name string) string {
	return path.Join(resourceType, namespace, name)
}

// TODO: handle more complex plural cases
func pluralToSingular(plural string) string {
	return plural[:len(plural)-1]
}

func generateResourceKeyFromRestCall(verb, resourceType, namespace, name string, object interface{}) string {
	if verb == HTTP_POST {
		if o, err := meta.Accessor(object); err == nil {
			return generateResourceKey(pluralToSingular(resourceType), namespace, o.GetName())
		} else {
			return generateResourceKey(pluralToSingular(resourceType), namespace, name)
		}
	} else {
		return generateResourceKey(pluralToSingular(resourceType), namespace, name)
	}
}

func getResourceTypeFromObj(object interface{}) string {
	objectUnstructured, ok := object.(*unstructured.Unstructured)
	if ok {
		return strings.ToLower(fmt.Sprint(objectUnstructured.Object["kind"]))
	} else {
		resourceType := reflect.TypeOf(object).String()
		tokens := strings.Split(resourceType, ".")
		return strings.ToLower(tokens[len(tokens)-1])
	}
}

func extractNameNamespaceFromObj(object interface{}) (string, string) {
	if o, err := meta.Accessor(object); err == nil {
		return o.GetName(), o.GetNamespace()
	}
	return "", ""
}

func isSameObjectClientSide(object interface{}, namespace string, name string) bool {
	extractedName, extractedNamespace := extractNameNamespaceFromObj(object)
	return extractedNamespace == namespace && extractedName == name
}

func getReconcilerFromStackTrace() string {
	// reflect.TypeOf(c.Do).String(): *controllers.NifiClusterTaskReconciler
	stacktrace := string(debug.Stack())
	// log.Println(stacktrace)
	stacks := strings.Split(stacktrace, "\n")
	var stacksPruned []string
	for _, stack := range stacks {
		if !strings.HasPrefix(stack, "\t") {
			stacksPruned = append(stacksPruned, stack)
		}
	}
	reconcilerType := ""
	for i := range stacksPruned {
		// We parse the stacktrace from bottom
		index := len(stacksPruned) - 1 - i
		stack := stacksPruned[index]
		if strings.HasPrefix(stack, "sigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller).reconcileHandler(") {
			if index > 0 {
				upper_stack := stacksPruned[index-1]
				if strings.HasPrefix(upper_stack, "sigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller).Reconcile(") {
					if index > 1 {
						upper_upper_stack := stacksPruned[index-2]
						if strings.Contains(upper_upper_stack, ".Reconcile(") && !strings.HasPrefix(upper_upper_stack, "sigs.k8s.io/controller-runtime/") {
							reconcilerType = upper_upper_stack[:strings.Index(upper_upper_stack, ".Reconcile(")]
							break
						} else {
							break
						}
					}
				} else if strings.Contains(upper_stack, ".Reconcile(") && !strings.HasPrefix(upper_stack, "sigs.k8s.io/controller-runtime/") {
					reconcilerType = upper_stack[:strings.Index(upper_stack, ".Reconcile(")]
					break
				} else {
					break
				}
			}
		}
	}
	if reconcilerType == "" {
		reconcilerType = UNKNOWN_RECONCILER_TYPE
	}
	return reconcilerType
}

func getResourceNamespaceNameFromAPIKey(key string) (string, string, error) {
	namespace := ""
	name := ""
	tokens := strings.Split(key, "/")
	if len(tokens) < 4 {
		// log.Printf("unrecognizable key %s\n", key)
		return namespace, name, fmt.Errorf("tokens len should be >= 4")
	}
	namespace = tokens[len(tokens)-2]
	name = tokens[len(tokens)-1]
	return namespace, name, nil
}

func LogAPIEvent(eventType, key string, object interface{}) {
	namespace, name, err := getResourceNamespaceNameFromAPIKey(key)
	if err != nil {
		return
	}
	if namespace != "default" {
		return
	}
	jsonObject, err := json.Marshal(object)
	if err != nil {
		printSerializationError(err)
		return
	}
	resourceType := getResourceTypeFromObj(object)
	log.Printf("[SIEVE-API-EVENT]\t%s\t%s\t%s\t%s\t%s\t%s\n", eventType, key, resourceType, namespace, name, string(jsonObject))
}
