package sonar

import (
	"io/ioutil"
	"log"
	"net/rpc"
	"os"
	"strings"
	"sync"

	"gopkg.in/yaml.v2"
)

var defaultHostPort string = "kind-control-plane:12345"
var connectionError string = "[sonar] connectionError"
var replyError string = "[sonar] replyError"
var hostError string = "[sonar] hostError"
var jsonError string = "[sonar] jsonError"
var config map[string]interface{} = nil

var taintMap sync.Map = sync.Map{}

const TIME_TRAVEL string = "time-travel"
const OBS_GAP string = "observability-gap"
const ATOM_VIO string = "atomicity-violation"
const LEARN string = "learn"
const TEST string = "test"

func checkMode(mode string) bool {
	if config == nil {
		config, _ = getConfig()
	}
	if config == nil {
		return false
	}
	if modeInConfig, ok := config["mode"]; ok {
		return modeInConfig.(string) == mode
	} else {
		log.Println("[sonar] no mode field in config")
		return false
	}
}

func checkStage(stage string) bool {
	if config == nil {
		config, _ = getConfig()
	}
	if config == nil {
		return false
	}
	if stageInConfig, ok := config["stage"]; ok {
		return stageInConfig.(string) == stage
	} else {
		log.Println("[sonar] no stage field in config")
		return false
	}
}

func checkTimeTravelTiming(timing string) bool {
	if checkStage(TEST) && checkMode(TIME_TRAVEL) {
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
	config, _ := getConfig()
	hostPort := defaultHostPort
	if config != nil {
		if val, ok := config["server-endpoint"]; ok {
			hostPort = val.(string)
		}
	}
	log.Println(hostPort)
	client, err := rpc.Dial("tcp", hostPort)
	if err != nil {
		log.Printf("[sonar] error in setting up connection to %s due to %v\n", hostPort, err)
		return nil, err
	}
	return client, nil
}

func getConfigFromEnv() map[string]interface{} {
	if _, ok := os.LookupEnv("SONAR-MODE"); ok {
		configFromEnv := make(map[string]interface{})
		for _, e := range os.Environ() {
			pair := strings.SplitN(e, "=", 2)
			envKey := pair[0]
			envVal := pair[1]
			if strings.HasPrefix(envKey, "SONAR-") {
				newKey := strings.ToLower(strings.TrimPrefix(envKey, "SONAR-"))
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

func getConfig() (map[string]interface{}, error) {
	configFromEnv := getConfigFromEnv()
	if configFromEnv != nil {
		log.Printf("[sonar] configFromEnv:\n%v\n", configFromEnv)
		return configFromEnv, nil
	}
	configPath := "sonar.yaml"
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		configPath = "/sonar.yaml"
	}
	data, err := ioutil.ReadFile(configPath)
	if err != nil {
		return nil, err
	}
	configFromYaml := make(map[string]interface{})
	err = yaml.Unmarshal([]byte(data), &configFromYaml)
	if err != nil {
		return nil, err
	}
	log.Printf("[sonar] configFromYaml:\n%v\n", configFromYaml)
	return configFromYaml, nil
}

func printError(err error, text string) {
	log.Printf("[sonar][error] %s due to: %v \n", text, err)
}

func checkResponse(response Response, reqName string) {
	if response.Ok {
		log.Printf("[sonar][%s] receives good response: %s\n", reqName, response.Message)
	} else {
		log.Printf("[sonar][error][%s] receives bad response: %s\n", reqName, response.Message)
	}
}

func regularizeType(rtype string) string {
	tokens := strings.Split(rtype, ".")
	return strings.ToLower(tokens[len(tokens)-1])
}

func pluralToSingle(rtype string) string {
	if rtype == "endpoints" {
		return rtype
	} else if strings.HasSuffix(rtype, "s") {
		return rtype[:len(rtype)-1]
	} else {
		return rtype
	}
}
