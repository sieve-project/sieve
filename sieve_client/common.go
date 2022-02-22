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

	"gopkg.in/yaml.v2"
	"k8s.io/apimachinery/pkg/api/meta"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
)

const STALE_STATE string = "stale-state"
const UNOBSERVED_STATE string = "unobserved-state"
const INTERMEDIATE_STATE string = "intermediate-state"
const LEARN string = "learn"
const TEST string = "test"
const UNKNOWN_RECONCILER_TYPE = "unknown"

// TODO(xudong): make SIEVE_SERVER_ADDR configurable
const SIEVE_SERVER_ADDR string = "kind-control-plane:12345"
const SIEVE_CONN_ERR string = "[SIEVE CONN ERR]"
const SIEVE_REPLY_ERR string = "[SIEVE REPLY ERR]"
const SIEVE_HOST_ERR string = "[SIEVE HOST ERR]"
const SIEVE_JSON_ERR string = "[SIEVE JSON ERR]"
const SIEVE_CONFIG_ERR string = "[SIEVE CONFIG ERR]"

var config map[string]interface{} = nil
var triggerDefinitions map[string][]map[interface{}]interface{} = make(map[string][]map[interface{}]interface{})

// var exists = struct{}{}

// var taintMap sync.Map = sync.Map{}

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
	for triggerResourceKey, triggers := range triggerDefinitions {
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
	for triggerResourceKey, triggers := range triggerDefinitions {
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

func internalLoadTriggerDefinitions(trigger map[interface{}]interface{}) error {
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
		resourceKeyRaw, ok := condition["resourceKey"]
		if !ok {
			return fmt.Errorf("cannot find resourceKey in trigger[\"definitions\"][%d][\"condition\"]", idx)
		}
		resourceKey, ok := resourceKeyRaw.(string)
		if !ok {
			return fmt.Errorf("cannot convert trigger[\"definitions\"][%d][\"condition\"][\"resourcekey\"] to string", idx)
		}
		if _, ok := triggerDefinitions[resourceKey]; !ok {
			triggerDefinitions[resourceKey] = []map[interface{}]interface{}{}
		}
		triggerDefinitions[resourceKey] = append(triggerDefinitions[resourceKey], definition)
	}
	return nil
}

func loadTriggerDefinitions(testPlan map[string]interface{}) error {
	actions, ok := testPlan["actions"].([]interface{})
	if !ok {
		return fmt.Errorf("cannot convert testPlan[\"actions\"] to []interface{}")
	}
	for idx, val := range actions {
		action, ok := val.(map[interface{}]interface{})
		if !ok {
			return fmt.Errorf("cannot convert testPlan[\"actions\"][%d] to []interface{}", idx)
		}
		trigger, ok := action["trigger"].(map[interface{}]interface{})
		if !ok {
			return fmt.Errorf("cannot convert testPlan[\"actions\"][%d][\"trigger\"] to []interface{}", idx)
		}
		err := internalLoadTriggerDefinitions(trigger)
		if err != nil {
			return err
		}
	}
	log.Printf("triggerDefinitions:\n%v\n", triggerDefinitions)
	return nil
}

func loadSieveConfigFromEnv() error {
	if config != nil {
		return nil
	}
	if _, ok := os.LookupEnv("sieveTestPlan"); ok {
		configFromEnv := make(map[string]interface{})
		data := os.Getenv("sieveTestPlan")
		err := yaml.Unmarshal([]byte(data), &configFromEnv)
		if err != nil {
			printError(err, SIEVE_JSON_ERR)
			return fmt.Errorf("fail to load from env")
		}
		log.Printf("config from env:\n%v\n", configFromEnv)
		config = configFromEnv
		err = loadTriggerDefinitions(configFromEnv)
		if err != nil {
			printError(err, SIEVE_CONFIG_ERR)
			return fmt.Errorf("fail to load from env")
		}
	} else {
		return fmt.Errorf("fail to load from env")
	}
	return nil
}

func loadSieveConfigFromConfigMap(eventType, key string, object interface{}) error {
	tokens := strings.Split(key, "/")
	name := tokens[len(tokens)-1]
	rtype := regularizeType(object)
	if name == "sieve-testing-global-config" && eventType == "ADDED" && rtype == "configmap" {
		log.Printf("[sieve] configmap map seen: %s, %s, %v\n", eventType, key, object)
		jsonObject, err := json.Marshal(object)
		if err != nil {
			printError(err, SIEVE_JSON_ERR)
			return fmt.Errorf("fail to load from configmap")
		}
		configMapObject := make(map[string]interface{})
		err = yaml.Unmarshal(jsonObject, &configMapObject)
		if err != nil {
			printError(err, SIEVE_JSON_ERR)
			return fmt.Errorf("fail to load from configmap")
		}
		log.Printf("[sieve] config map is %v\n", configMapObject)
		configFromConfigMapData := make(map[string]interface{})
		configMapData, ok := configMapObject["Data"].(map[interface{}]interface{})
		if !ok {
			log.Printf("[sieve] cannot convert to map[interface{}]interface{}")
			return fmt.Errorf("fail to load from configmap")
		}
		if str, ok := configMapData["sieveTestPlan"].(string); ok {
			err = yaml.Unmarshal([]byte(str), &configFromConfigMapData)
			if err != nil {
				printError(err, SIEVE_JSON_ERR)
				return fmt.Errorf("fail to load from configmap")
			}
			log.Printf("config from configMap:\n%v\n", configFromConfigMapData)
			config = configFromConfigMapData
			err = loadTriggerDefinitions(configFromConfigMapData)
			if err != nil {
				printError(err, SIEVE_CONFIG_ERR)
				return fmt.Errorf("fail to load from configmap")
			}
		} else {
			log.Printf("cannot convert %v to string", configMapData["sieveTestPlan"])
			return fmt.Errorf("fail to load from configmap")
		}
	}
	return nil
}

func getCRDs() []string {
	crds := []string{}
	if cs, ok := config["CRDList"]; ok {
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
			log.Println("crd-list wrong type")
		}
	} else {
		log.Println("do not find CRDList from config")
	}
	return crds
}

func newClient() (*rpc.Client, error) {
	hostPort := SIEVE_SERVER_ADDR
	if val, ok := config["serverEndpoint"]; ok {
		hostPort = val.(string)
	}
	client, err := rpc.Dial("tcp", hostPort)
	if err != nil {
		log.Printf("[sieve] error in setting up connection to %s due to %v\n", hostPort, err)
		return nil, err
	}
	return client, nil
}

func printError(err error, text string) {
	log.Printf("[sieve][error] %s due to: %v \n", text, err)
}

func checkResponse(response Response, reqName string) {
	if response.Ok {
		// log.Printf("[sieve][%s] receives good response: %s\n", reqName, response.Message)
	} else {
		log.Printf("[sieve][error][%s] receives bad response: %s\n", reqName, response.Message)
	}
}

func generateResourceKey(resourceKey, namespace, name string) string {
	return path.Join(resourceKey, namespace, name)
}

func regularizeType(object interface{}) string {
	objectUnstructured, ok := object.(*unstructured.Unstructured)
	if ok {
		return strings.ToLower(fmt.Sprint(objectUnstructured.Object["kind"]))
	} else {
		rtype := reflect.TypeOf(object).String()
		tokens := strings.Split(rtype, ".")
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
	return reconcilerType
}
