package main

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"os/exec"
	"sync"
	"time"

	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/client-go/deprecated/scheme"
	"k8s.io/client-go/kubernetes"
	restclient "k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
	"k8s.io/client-go/tools/remotecommand"
	sonar "sonar.client/pkg/sonar"
)

var globalCntToRestart int = 0
var mutex = &sync.Mutex{}

type RestartConfig struct {
	eventType    string
	resourceType string
	apiserver    string
	times        int
}

func NewStalenessListener(config map[interface{}]interface{}) *StalenessListener {
	server := &stalenessServer{
		apiserverHostname:    config["apiserver"].(string),
		expectedResourceType: config["resource-type"].(string),
		restartConfig: RestartConfig{
			eventType:    config["restart-event-type"].(string),
			resourceType: config["restart-resource-type"].(string),
			apiserver:    config["restart-apiserver"].(string),
			times:        config["restart-times"].(int),
		},
	}
	listener := &StalenessListener{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

type StalenessListener struct {
	Server *stalenessServer
}

func (l *StalenessListener) Echo(request *sonar.EchoRequest, response *sonar.Response) error {
	*response = sonar.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *StalenessListener) WaitBeforeProcessEvent(request *sonar.WaitBeforeProcessEventRequest, response *sonar.Response) error {
	return l.Server.WaitBeforeProcessEvent(request, response)
}

type stalenessServer struct {
	apiserverHostname    string
	expectedResourceType string
	restartConfig        RestartConfig
}

func (s *stalenessServer) Start() {
	log.Println("start stalenessServer...")
}

func (s *stalenessServer) WaitBeforeProcessEvent(request *sonar.WaitBeforeProcessEventRequest, response *sonar.Response) error {
	if request.ResourceType == s.expectedResourceType {
		log.Printf("WaitBeforeProcessEvent: EventType: %s, ResourceType: %s, Hostname: %s\n", request.EventType, request.ResourceType, request.Hostname)
	}
	if s.shouldRestart(request) {
		go s.waitAndRestartComponent(160)
	}
	if request.EventType == "DELETED" && request.ResourceType == s.expectedResourceType && request.Hostname == s.apiserverHostname {
		log.Printf("Should sleep here...")
		*response = sonar.Response{Message: request.Hostname, Ok: true, Wait: 800}
		return nil
	}
	*response = sonar.Response{Message: request.Hostname, Ok: true, Wait: 0}
	return nil
}

func (s *stalenessServer) waitAndRestartComponent(dur int) {
	time.Sleep(time.Duration(dur) * time.Second)
	s.restartComponent()
}

func (s *stalenessServer) shouldRestart(request *sonar.WaitBeforeProcessEventRequest) bool {
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

func (s *stalenessServer) restartComponent() {
	config, err := clientcmd.BuildConfigFromFlags("", "/root/.kube/config")
	checkError(err)
	clientset, err := kubernetes.NewForConfig(config)
	checkError(err)
	labelSelector := metav1.LabelSelector{MatchLabels: map[string]string{"name": "cassandra-operator"}}
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

	cmd1 := exec.Command("./util.sh", "crash", pod.Name)
	err = cmd1.Run()
	checkError(err)
	fmt.Println("crash")

	cmd2 := exec.Command("./util.sh", "restart", pod.Name)
	err = cmd2.Run()
	checkError(err)
	fmt.Println("restart")
}

func (s *stalenessServer) execInPod(config *restclient.Config, podName string, cmd []string) {
	clientset, err := kubernetes.NewForConfig(config)
	checkError(err)
	req := clientset.CoreV1().RESTClient().Post().Resource("pods").Name(podName).Namespace("default").SubResource("exec")
	option := &v1.PodExecOptions{
		Command: cmd,
		Stdout:  true,
		Stderr:  true,
	}
	req.VersionedParams(
		option,
		scheme.ParameterCodec,
	)
	exec, err := remotecommand.NewSPDYExecutor(config, "POST", req.URL())
	checkError(err)
	var buf bytes.Buffer
	err = exec.Stream(remotecommand.StreamOptions{
		Stdin:  nil,
		Stdout: &buf,
		Stderr: &buf,
	})
	checkError(err)
	fmt.Printf("cmd output: %s\n", buf.String())
}
