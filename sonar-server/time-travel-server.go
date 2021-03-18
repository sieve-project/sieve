package main

import (
	"context"
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
	apiserver    string
	resourceType string
	eventType    string
	duration     int
}

type RestartConfig struct {
	pod          string
	apiserver    string
	resourceType string
	eventType    string
	times        int
	wait         int
}

// The listener is actually a wrapper around the server.
func NewTimeTravelListener(config map[interface{}]interface{}) *TimeTravelListener {
	server := &stalenessServer{
		project: config["project"].(string),
		freezeConfig: FreezeConfig{
			apiserver:    config["freeze-apiserver"].(string),
			resourceType: config["freeze-resource-type"].(string),
			eventType:    config["freeze-event-type"].(string),
			duration:     config["freeze-duration"].(int),
		},
		restartConfig: RestartConfig{
			pod:          config["restart-pod"].(string),
			apiserver:    config["restart-apiserver"].(string),
			resourceType: config["restart-resource-type"].(string),
			eventType:    config["restart-event-type"].(string),
			times:        config["restart-times"].(int),
			wait:         config["restart-wait"].(int),
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

// NotifyBeforeProcessEvent is called when apiserver invokes `processEvent`.
// It will decide (1) whether to freeze an apiserver and (2) whether to restart a controller
func (l *TimeTravelListener) NotifyBeforeProcessEvent(request *sonar.NotifyBeforeProcessEventRequest, response *sonar.Response) error {
	return l.Server.NotifyBeforeProcessEvent(request, response)
}

type stalenessServer struct {
	project string
	freezeConfig  FreezeConfig
	restartConfig RestartConfig
}

func (s *stalenessServer) Start() {
	log.Println("start stalenessServer...")
}

func (s *stalenessServer) NotifyBeforeProcessEvent(request *sonar.NotifyBeforeProcessEventRequest, response *sonar.Response) error {
	if request.ResourceType != s.freezeConfig.resourceType && request.ResourceType != s.restartConfig.resourceType {
		*response = sonar.Response{Message: request.Hostname, Ok: true, Wait: 0}
		return nil
	}
	log.Printf("NotifyBeforeProcessEvent: EventType: %s, ResourceType: %s, Hostname: %s\n", request.EventType, request.ResourceType, request.Hostname)
	if s.shouldRestart(request) {
		log.Printf("Should restart here...")
		go s.waitAndRestartComponent()
	}
	if s.shouldFreeze(request) {
		log.Printf("Should sleep here...")
		*response = sonar.Response{Message: request.Hostname, Ok: true, Wait: s.freezeConfig.duration}
		return nil
	}
	*response = sonar.Response{Message: request.Hostname, Ok: true, Wait: 0}
	return nil
}

func (s *stalenessServer) waitAndRestartComponent() {
	time.Sleep(time.Duration(s.restartConfig.wait) * time.Second)
	s.restartComponent(s.project, s.restartConfig.pod)
}

func (s *stalenessServer) shouldFreeze(request *sonar.NotifyBeforeProcessEventRequest) bool {
	return s.freezeConfig.apiserver == request.Hostname && s.freezeConfig.eventType == request.EventType && s.freezeConfig.resourceType == request.ResourceType
}

// Condition for restart controller:
// [apiserver] receives the event with [eventType] for [resourceType] for the [times] times.
// The condition is configured by users, and is relatively too low level.
// TODO: expose a high level interface to users
// TODO: decouple crash and restart
// TODO: consider more information from the apiserver
func (s *stalenessServer) shouldRestart(request *sonar.NotifyBeforeProcessEventRequest) bool {
	if s.restartConfig.apiserver == request.Hostname && s.restartConfig.eventType == request.EventType && s.restartConfig.resourceType == request.ResourceType {
		mutex.Lock()
		defer mutex.Unlock()
		log.Println("increment cnt")
		globalCntToRestart++
		if globalCntToRestart == s.restartConfig.times {
			return true
		}
	}
	return false
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
