package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os/exec"
	"sync"
	"time"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
	sonar "sonar.client"
)

var globalCntToRestart int = 0
var mutex = &sync.Mutex{}

type FreezeConfig struct {
	apiserver string
	// resourceType string
	// eventType    string
	duration int
	crucial  string
}

type RestartConfig struct {
	pod       string
	apiserver string
	// resourceType string
	// eventType    string
	// times        int
	// wait         int
}

// The listener is actually a wrapper around the server.
func NewTimeTravelListener(config map[interface{}]interface{}) *TimeTravelListener {
	server := &stalenessServer{
		project:    config["project"].(string),
		afterPause: false,
		freezeConfig: FreezeConfig{
			apiserver: config["freeze-apiserver"].(string),
			// resourceType: config["freeze-resource-type"].(string),
			// eventType:    config["freeze-event-type"].(string),
			duration: config["freeze-duration"].(int),
			crucial:  config["freeze-crucial"].(string),
		},
		restartConfig: RestartConfig{
			pod:       config["restart-pod"].(string),
			apiserver: config["restart-apiserver"].(string),
			// resourceType: config["restart-resource-type"].(string),
			// eventType:    config["restart-event-type"].(string),
			// times:        config["restart-times"].(int),
			// wait:         config["restart-wait"].(int),
		},
	}
	listener := &TimeTravelListener{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

type TimeTravelListener struct {
	Server *stalenessServer
}

// Echo is just for testing.
func (l *TimeTravelListener) Echo(request *sonar.EchoRequest, response *sonar.Response) error {
	*response = sonar.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *TimeTravelListener) NotifyTimeTravelCrucialEvent(request *sonar.NotifyTimeTravelCrucialEventRequest, response *sonar.Response) error {
	return l.Server.NotifyTimeTravelCrucialEvent(request, response)
}

func (l *TimeTravelListener) NotifyTimeTravelSideEffect(request *sonar.NotifyTimeTravelSideEffectRequest, response *sonar.Response) error {
	return l.Server.NotifyTimeTravelSideEffect(request, response)
}

type stalenessServer struct {
	project       string
	afterPause    bool
	freezeConfig  FreezeConfig
	restartConfig RestartConfig
}

func (s *stalenessServer) Start() {
	log.Println("start stalenessServer...")
}

func strToMap(str string) map[string]interface{} {
	m := make(map[string]interface{})
	err := json.Unmarshal([]byte(str), &m)
	if err != nil {
		log.Fatalf("cannot unmarshal to map: %s\n", str)
	}
	return m
}

func (s *stalenessServer) equivalentEvent(crucialEvent, currentEvent map[string]interface{}) bool {
	for key, val := range crucialEvent {
		if _, ok := currentEvent[key]; !ok {
			return false
		}
		switch v := val.(type) {
		case int:
			if e, ok := currentEvent[key].(int); ok {
				return v == e
			} else {
				return false
			}
		case string:
			if v == "sonar-exist" {
				return true
			} else if e, ok := currentEvent[key].(string); ok {
				return v == e
			} else {
				return false
			}
		case map[string]interface{}:
			if e, ok := currentEvent[key].(map[string]interface{}); ok {
				if !s.equivalentEvent(v, e) {
					return false
				}
			} else {
				return false
			}
		default:
			log.Printf("Unsupported type: %v", v)
		}
	}
	return true
}

func (s *stalenessServer) NotifyTimeTravelCrucialEvent(request *sonar.NotifyTimeTravelCrucialEventRequest, response *sonar.Response) error {
	log.Printf("NotifyTimeTravelCrucialEvent: Hostname: %s\n", request.Hostname)
	if s.freezeConfig.apiserver != request.Hostname {
		*response = sonar.Response{Message: request.Hostname, Ok: true}
		return nil
	}
	currentEvent := strToMap(request.Object)
	crucialEvent := strToMap(s.freezeConfig.crucial)
	log.Printf("[sonar][crucialEvent] %s\n", request.Object)
	log.Printf("[sonar][currentEvent] %s\n", s.freezeConfig.crucial)
	if s.shouldPause(crucialEvent, currentEvent) {
		s.afterPause = true
		log.Println("[sonar] should sleep here")
		time.Sleep(time.Duration(s.freezeConfig.duration) * time.Second)
		log.Println("[sonar] sleep over")
	}
	*response = sonar.Response{Message: request.Hostname, Ok: true}
	return nil
}

func (s *stalenessServer) NotifyTimeTravelSideEffect(request *sonar.NotifyTimeTravelSideEffectRequest, response *sonar.Response) error {
	log.Printf("NotifyTimeTravelSideEffect: Hostname: %s\n", request.Hostname)
	if s.restartConfig.apiserver != request.Hostname {
		*response = sonar.Response{Message: request.Hostname, Ok: true}
		return nil
	}
	log.Printf("[sonar][sideeffect] %s %s %s %s", request.Name, request.Namespace, request.ResourceType, request.EventType)
	if s.shouldRestart() {
		log.Println("[sonar] should restart here")
		s.afterPause = false
		go s.waitAndRestartComponent()
	}
	*response = sonar.Response{Message: request.Hostname, Ok: true}
	return nil
}

func (s *stalenessServer) waitAndRestartComponent() {
	time.Sleep(time.Duration(10) * time.Second)
	s.restartComponent(s.project, s.restartConfig.pod)
}

func (s *stalenessServer) shouldPause(crucialEvent, currentEvent map[string]interface{}) bool {
	return s.equivalentEvent(crucialEvent, currentEvent)
}

func (s *stalenessServer) shouldRestart() bool {
	return s.afterPause
}

// The controller to restart is identified by `restart-pod` in the configuration.
// `restart-pod` is a label to identify the pod where the controller is running.
// We do not directly use pod name because the pod belongs to a deployment so its name is not fixed.
func (s *stalenessServer) restartComponent(project, podLabel string) {
	config, err := clientcmd.BuildConfigFromFlags("", "/root/.kube/config")
	checkError(err)
	clientset, err := kubernetes.NewForConfig(config)
	checkError(err)
	labelSelector := metav1.LabelSelector{MatchLabels: map[string]string{"name": podLabel}}
	listOptions := metav1.ListOptions{
		LabelSelector: labels.Set(labelSelector.MatchLabels).String(),
	}
	pods, err := clientset.CoreV1().Pods("default").List(context.TODO(), listOptions)
	checkError(err)
	if len(pods.Items) == 0 {
		log.Fatalln("didn't get any pod")
	}
	pod := pods.Items[0]
	log.Printf("get operator pod: %s", pod.Name)

	// The way we crash and restart the controller is not very graceful here.
	// The util.sh is a simple script with commands to kill the controller process
	// and restart the controller process.
	// Why not directly call the commands?
	// The command needs nested quotation marks and
	// I find parsing nested quotation marks are tricky in golang.
	// TODO: figure out how to make nested quotation marks work
	cmd1 := exec.Command("./util.sh", project, "crash", pod.Name)
	err = cmd1.Run()
	checkError(err)
	fmt.Println("crash")

	cmd2 := exec.Command("./util.sh", project, "restart", pod.Name)
	err = cmd2.Run()
	checkError(err)
	fmt.Println("restart")
}
