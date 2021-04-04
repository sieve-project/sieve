package sonar

import (
	"strings"
	"io/ioutil"
	"net/rpc"
	"log"
	"sync"

	"gopkg.in/yaml.v2"
)

var hostPort string = "kind-control-plane:12345"
var connectionError string = "[sonar] connectionError"
var replyError string = "[sonar] replyError"
var hostError string = "[sonar] hostError"
var configError string = "[sonar] configError"
var jsonError string = "[sonar] jsonError"
var config map[string]interface{} = nil
var sparseRead string = "sparse-read"
var timeTravel string = "time-travel"
var learn string = "learn"
var taintMap sync.Map = sync.Map{}

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

func checkTimeTravelTiming(timing string) bool {
	if checkMode(timeTravel) {
		if timingInConfig, ok := config["timing"]; ok {
			return timingInConfig.(string) == timing
		} else {
			return "after" == timing
		}
	}
	return false
}

func getCRDs() []string {
	crds := []string{}
	if cs, ok := config["crds"]; ok {
		cs := cs.([]interface{})
		for _, c := range cs {
			crds = append(crds, c.(string))
		}
	}
	return crds
}

func newClient() (*rpc.Client, error) {
	client, err := rpc.Dial("tcp", hostPort)
	if err != nil {
		log.Printf("[sonar] error in setting up connection to %s due to %v\n", hostPort, err)
		return nil, err
	}
	return client, nil
}

func getConfig() (map[string]interface{}, error) {
	data, err := ioutil.ReadFile("/sonar.yaml")
	if err != nil {
		return nil, err
	}
	m := make(map[string]interface{})
	err = yaml.Unmarshal([]byte(data), &m)
	if err != nil {
		return nil, err
	}
	log.Printf("[sonar] config:\n%v\n", m)
	return m, nil
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
	return strings.ToLower(tokens[len(tokens) - 1])
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
