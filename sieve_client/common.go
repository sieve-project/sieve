package sieve

import (
	"encoding/json"
	"fmt"
	"log"
	"net/rpc"
	"os"
	"reflect"
	"runtime/debug"
	"strings"
	"sync"

	"gopkg.in/yaml.v2"
	"k8s.io/apimachinery/pkg/api/meta"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
)

const STALE_STATE string = "stale-state"
const UNOBSR_STATE string = "unobserved-state"
const INTERMEDIATE_STATE string = "intermediate-state"
const LEARN string = "learn"
const TEST string = "test"

// TODO(xudong): make SIEVE_SERVER_ADDR configurable
const SIEVE_SERVER_ADDR string = "kind-control-plane:12345"
const SIEVE_CONN_ERR string = "[SIEVE CONN ERR]"
const SIEVE_REPLY_ERR string = "[SIEVE REPLY ERR]"
const SIEVE_HOST_ERR string = "[SIEVE HOST ERR]"
const SIEVE_JSON_ERR string = "[SIEVE JSON ERR]"

var config map[string]interface{} = nil
var configFromConfigMapData map[string]interface{} = nil
var configMapReady = false

var taintMap sync.Map = sync.Map{}

func loadSieveConfig() error {
	if config == nil {
		var err error = nil
		config, err = getConfig()
		if err == nil {
			log.Println(config)
		} else {
			return err
		}
	}
	return nil
}

func getConfigFromEnv() map[string]interface{} {
	if _, ok := os.LookupEnv("SIEVE-MODE"); ok {
		configFromEnv := make(map[string]interface{})
		for _, e := range os.Environ() {
			pair := strings.SplitN(e, "=", 2)
			envKey := pair[0]
			envVal := pair[1]
			if strings.HasPrefix(envKey, "SIEVE-") {
				newKey := strings.ToLower(strings.TrimPrefix(envKey, "SIEVE-"))
				if strings.HasSuffix(newKey, "-list") {
					configFromEnv[newKey] = strings.Split(envVal, ",")
				} else {
					configFromEnv[newKey] = envVal
				}
			}
		}
		return configFromEnv
	} else {
		return nil
	}
}

func loadSieveConfigMap(eventType, key string, object interface{}) {
	tokens := strings.Split(key, "/")
	name := tokens[len(tokens)-1]
	rtype := regularizeType(object)
	if name == "sieve-testing-global-config" {
		log.Printf("[sieve] configmap map seen: %s, %s, %v\n", eventType, key, object)
		if eventType == "ADDED" && rtype == "configmap" {
			jsonObject, err := json.Marshal(object)
			if err != nil {
				printError(err, SIEVE_JSON_ERR)
				return
			}
			configMapObject := make(map[string]interface{})
			err = yaml.Unmarshal(jsonObject, &configMapObject)
			if err != nil {
				printError(err, SIEVE_JSON_ERR)
				return
			}
			log.Printf("[sieve] config map is %v\n", configMapObject)
			configFromConfigMapData = make(map[string]interface{})
			configMapData, ok := configMapObject["Data"].(map[interface{}]interface{})
			if !ok {
				log.Printf("[sieve] cannot convert to map[interface{}]interface{}")
				return
			}
			for k, v := range configMapData {
				newKey := strings.ToLower(strings.TrimPrefix(k.(string), "SIEVE-"))
				newVal := v
				configFromConfigMapData[newKey] = newVal
			}
			configMapReady = true
		}
	}
}

func getConfig() (map[string]interface{}, error) {
	if configMapReady {
		return configFromConfigMapData, nil
	}
	configFromEnv := getConfigFromEnv()
	if configFromEnv != nil {
		return configFromEnv, nil
	}
	return nil, fmt.Errorf("config is not found")
}

func checkMode(mode string) bool {
	if modeInConfig, ok := config["mode"]; ok {
		return modeInConfig.(string) == mode
	} else {
		log.Println("[sieve] no mode field in config")
		return false
	}
}

func checkStage(stage string) bool {
	if stageInConfig, ok := config["stage"]; ok {
		return stageInConfig.(string) == stage
	} else {
		log.Println("[sieve] no stage field in config")
		return false
	}
}

func checkTimeTravelTiming(timing string) bool {
	if checkStage(TEST) && checkMode(STALE_STATE) {
		if timingInConfig, ok := config["timing"]; ok {
			return timingInConfig.(string) == timing
		} else {
			return timing == "after"
		}
	}
	return false
}

func getCRDs() []string {
	crds := []string{}
	if cs, ok := config["crd-list"]; ok {
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
	}
	return crds
}

func newClient() (*rpc.Client, error) {
	hostPort := SIEVE_SERVER_ADDR
	if val, ok := config["server-endpoint"]; ok {
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

func pluralToSingle(rtype string) string {
	if rtype == "endpoints" {
		return rtype
	} else if strings.HasSuffix(rtype, "ches") {
		// TODO: this is very dirty hack. We should have a systematic way to get resource type
		return rtype[:len(rtype)-2]
	} else if strings.HasSuffix(rtype, "s") {
		return rtype[:len(rtype)-1]
	} else {
		return rtype
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
	stacks := strings.Split(stacktrace, "\n")
	var stacksPruned []string
	for _, stack := range stacks {
		if !strings.HasPrefix(stack, "\t") {
			stacksPruned = append(stacksPruned, stack)
		}
	}
	reconcilerType := ""
	for i, stack := range stacksPruned {
		if strings.HasPrefix(stack, "sigs.k8s.io/controller-runtime/pkg/internal/controller.(*Controller).reconcileHandler") {
			reconcilerLayer := stacksPruned[i-1]
			reconcilerType = reconcilerLayer[:strings.Index(reconcilerLayer, ".Reconcile(")]
			break
		}
	}
	return reconcilerType
}
