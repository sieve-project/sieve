package main

import (
	"context"
	"encoding/json"
	"log"
	"sync"
	"time"

	appsv1 "k8s.io/api/apps/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
	sonar "sonar.client"
)

var globalCntToRestart int = 0
var mutex = &sync.Mutex{}

// The listener is actually a wrapper around the server.
func NewTimeTravelListener(config map[interface{}]interface{}) *TimeTravelListener {
	server := &timeTravelServer{
		project:     config["project"].(string),
		seenPrev:    false,
		paused:      false,
		restarted:   false,
		pauseCh:     make(chan int),
		straggler:   config["straggler"].(string),
		crucialCur:  config["ce-diff-current"].(string),
		crucialPrev: config["ce-diff-previous"].(string),
		podLable:    config["operator-pod-label"].(string),
		frontRunner: config["front-runner"].(string),
		deployName:  config["deployment-name"].(string),
		namespace:   "default",
	}
	listener := &TimeTravelListener{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

type TimeTravelListener struct {
	Server *timeTravelServer
}

// Echo is just for testing.
func (l *TimeTravelListener) Echo(request *sonar.EchoRequest, response *sonar.Response) error {
	*response = sonar.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *TimeTravelListener) NotifyTimeTravelCrucialEvent(request *sonar.NotifyTimeTravelCrucialEventRequest, response *sonar.Response) error {
	return l.Server.NotifyTimeTravelCrucialEvent(request, response)
}

func (l *TimeTravelListener) NotifyTimeTravelRestartPoint(request *sonar.NotifyTimeTravelRestartPointRequest, response *sonar.Response) error {
	return l.Server.NotifyTimeTravelRestartPoint(request, response)
}

func (l *TimeTravelListener) NotifyTimeTravelSideEffects(request *sonar.NotifyTimeTravelSideEffectsRequest, response *sonar.Response) error {
	return l.Server.NotifyTimeTravelSideEffects(request, response)
}

type timeTravelServer struct {
	project     string
	straggler   string
	frontRunner string
	crucialCur  string
	crucialPrev string
	podLable    string
	seenPrev    bool
	paused      bool
	restarted   bool
	pauseCh     chan int
	deployName  string
	namespace   string
}

func (s *timeTravelServer) Start() {
	log.Println("start timeTravelServer...")
}

func strToMap(str string) map[string]interface{} {
	m := make(map[string]interface{})
	err := json.Unmarshal([]byte(str), &m)
	if err != nil {
		log.Fatalf("cannot unmarshal to map: %s\n", str)
	}
	return m
}

func deepCopyMap(src map[string]interface{}, dest map[string]interface{}) {
	if src == nil {
		log.Fatalf("src is nil. You cannot read from a nil map")
	}
	if dest == nil {
		log.Fatalf("dest is nil. You cannot insert to a nil map")
	}
	jsonStr, err := json.Marshal(src)
	if err != nil {
		log.Fatalf(err.Error())
	}
	err = json.Unmarshal(jsonStr, &dest)
	if err != nil {
		log.Fatalf(err.Error())
	}
}

func equivalentEventList(crucialEvent, currentEvent []interface{}) bool {
	if len(crucialEvent) != len(currentEvent) {
		return false
	}
	for i, val := range crucialEvent {
		switch v := val.(type) {
		case int64:
			if e, ok := currentEvent[i].(int64); ok {
				if v != e {
					return false
				}
			} else {
				return false
			}
		case float64:
			if e, ok := currentEvent[i].(float64); ok {
				if v != e {
					return false
				}
			} else {
				return false
			}
		case bool:
			if e, ok := currentEvent[i].(bool); ok {
				if v != e {
					return false
				}
			} else {
				return false
			}
		case string:
			if v == "SONAR-NON-NIL" || v == "SONAR-SKIP" {
				continue
			} else if e, ok := currentEvent[i].(string); ok {
				if v != e {
					return false
				}
			} else {
				return false
			}
		case map[string]interface{}:
			if e, ok := currentEvent[i].(map[string]interface{}); ok {
				if !equivalentEvent(v, e) {
					return false
				}
			} else {
				return false
			}
		default:
			log.Printf("Unsupported type: %v %T\n", v, v)
			return false
		}
	}
	return true
}

func equivalentEvent(crucialEvent, currentEvent map[string]interface{}) bool {
	for key, val := range crucialEvent {
		if _, ok := currentEvent[key]; !ok {
			return false
		}
		switch v := val.(type) {
		case int64:
			if e, ok := currentEvent[key].(int64); ok {
				if v != e {
					return false
				}
			} else {
				return false
			}
		case float64:
			if e, ok := currentEvent[key].(float64); ok {
				if v != e {
					return false
				}
			} else {
				return false
			}
		case bool:
			if e, ok := currentEvent[key].(bool); ok {
				if v != e {
					return false
				}
			} else {
				return false
			}
		case string:
			if v == "SONAR-NON-NIL" {
				continue
			} else if e, ok := currentEvent[key].(string); ok {
				if v != e {
					return false
				}
			} else {
				return false
			}
		case map[string]interface{}:
			if e, ok := currentEvent[key].(map[string]interface{}); ok {
				if !equivalentEvent(v, e) {
					return false
				}
			} else {
				return false
			}
		case []interface{}:
			if e, ok := currentEvent[key].([]interface{}); ok {
				if !equivalentEventList(v, e) {
					return false
				}
			} else {
				return false
			}
		default:
			log.Printf("Unsupported type: %v %T\n", v, v)
			return false
		}
	}
	return true
}

func equivalentEventSecondTry(crucialEvent, currentEvent map[string]interface{}) bool {
	if _, ok := currentEvent["metadata"]; ok {
		return false
	}
	if _, ok := crucialEvent["metadata"]; ok {
		copiedCrucialEvent := make(map[string]interface{})
		deepCopyMap(crucialEvent, copiedCrucialEvent)
		metadataMap := copiedCrucialEvent["metadata"]
		if m, ok := metadataMap.(map[string]interface{}); ok {
			for key := range m {
				copiedCrucialEvent[key] = m[key]
			}
			delete(copiedCrucialEvent, "metadata")
			return equivalentEvent(copiedCrucialEvent, currentEvent)
		} else {
			return false
		}
	} else {
		return false
	}
}

func isCrucial(crucialEvent, currentEvent map[string]interface{}) bool {
	if equivalentEvent(crucialEvent, currentEvent) {
		log.Println("Meet")
		return true
	} else if equivalentEventSecondTry(crucialEvent, currentEvent) {
		log.Println("Meet for the second try")
		return true
	} else {
		return false
	}
}

func (s *timeTravelServer) NotifyTimeTravelCrucialEvent(request *sonar.NotifyTimeTravelCrucialEventRequest, response *sonar.Response) error {
	log.Printf("NotifyTimeTravelCrucialEvent: Hostname: %s\n", request.Hostname)
	if s.straggler != request.Hostname {
		*response = sonar.Response{Message: request.Hostname, Ok: true}
		return nil
	}
	currentEvent := strToMap(request.Object)
	crucialCurEvent := strToMap(s.crucialCur)
	crucialPrevEvent := strToMap(s.crucialPrev)
	log.Printf("[sonar][current-event] %s\n", request.Object)
	if s.shouldPause(crucialCurEvent, crucialPrevEvent, currentEvent) {
		log.Println("[sonar] should sleep here")
		<-s.pauseCh
		log.Println("[sonar] sleep over")
	}
	*response = sonar.Response{Message: request.Hostname, Ok: true}
	return nil
}

func (s *timeTravelServer) NotifyTimeTravelRestartPoint(request *sonar.NotifyTimeTravelRestartPointRequest, response *sonar.Response) error {
	log.Printf("NotifyTimeTravelSideEffect: Hostname: %s\n", request.Hostname)
	if s.frontRunner != request.Hostname {
		*response = sonar.Response{Message: request.Hostname, Ok: true}
		return nil
	}
	log.Printf("[sonar][restart-point] %s %s %s %s\n", request.Name, request.Namespace, request.ResourceType, request.EventType)
	if s.shouldRestart() {
		log.Println("[sonar] should restart here")
		go s.waitAndRestartComponent()
	}
	*response = sonar.Response{Message: request.Hostname, Ok: true}
	return nil
}

func (s *timeTravelServer) NotifyTimeTravelSideEffects(request *sonar.NotifyTimeTravelSideEffectsRequest, response *sonar.Response) error {
	name, namespace := extractNameNamespace(request.Object)
	log.Printf("[SONAR-SIDE-EFFECT]\t%s\t%s\t%s\t%s\t%s\n", request.SideEffectType, request.ResourceType, namespace, name, request.Error)
	*response = sonar.Response{Message: request.SideEffectType, Ok: true}
	return nil
}

func (s *timeTravelServer) waitAndRestartComponent() {
	time.Sleep(time.Duration(10) * time.Second)
	s.restartComponent()
	time.Sleep(time.Duration(20) * time.Second)
	s.pauseCh <- 0
}

func (s *timeTravelServer) shouldPause(crucialCurEvent, crucialPrevEvent, currentEvent map[string]interface{}) bool {
	if !s.paused {
		if !s.seenPrev {
			if isCrucial(crucialPrevEvent, currentEvent) && (len(crucialCurEvent) == 0 || !isCrucial(crucialCurEvent, currentEvent)) {
				log.Println("Meet crucialPrevEvent: set seenPrev to true")
				s.seenPrev = true
			}
		} else {
			if isCrucial(crucialCurEvent, currentEvent) && (len(crucialPrevEvent) == 0 || !isCrucial(crucialPrevEvent, currentEvent)) {
				log.Println("Meet crucialCurEvent: set paused to true and start to pause")
				s.paused = true
				return true
			}
			// else if s.isCrucial(crucialPrevEvent, currentEvent) {
			// 	log.Println("Meet crucialPrevEvent: keep seenPrev as true")
			// 	// s.seenPrev = true
			// } else {
			// 	log.Println("Not meet anything: set seenPrev back to false")
			// 	s.seenPrev = false
			// }
		}
	}
	return false
}

func (s *timeTravelServer) shouldRestart() bool {
	if s.paused && !s.restarted {
		s.restarted = true
		return true
	} else {
		return false
	}
}


func (s *timeTravelServer) restartComponent() {
	masterUrl := "https://" + s.frontRunner + ":6443"
	config, err := clientcmd.BuildConfigFromFlags(masterUrl, "/root/.kube/config")
	checkError(err)
	clientset, err := kubernetes.NewForConfig(config)
	checkError(err)

	deployment, err := clientset.AppsV1().Deployments(s.namespace).Get(context.TODO(), s.deployName, metav1.GetOptions{})
	checkError(err)
	log.Println(deployment.Spec.Template.Spec.Containers[0].Env)

	clientset.AppsV1().Deployments(s.namespace).Delete(context.TODO(), s.deployName, metav1.DeleteOptions{})

	labelSelector := metav1.LabelSelector{MatchLabels: map[string]string{"sonartag": s.podLable}}
	listOptions := metav1.ListOptions{
		LabelSelector: labels.Set(labelSelector.MatchLabels).String(),
	}

	for true {
		time.Sleep(time.Duration(1) * time.Second)
		pods, err := clientset.CoreV1().Pods(s.namespace).List(context.TODO(), listOptions)
		checkError(err)
		if len(pods.Items) != 0 {
			log.Printf("operator pod not deleted yet\n")
		} else {
			log.Printf("operator pod gets deleted\n")
			break
		}
	}

	newDeployment := &appsv1.Deployment{
		ObjectMeta: metav1.ObjectMeta{
			Name:      deployment.ObjectMeta.Name,
			Namespace: deployment.ObjectMeta.Namespace,
			Labels:    deployment.ObjectMeta.Labels,
		},
		Spec: deployment.Spec,
	}

	containersNum := len(newDeployment.Spec.Template.Spec.Containers)
	for i := 0; i < containersNum; i++ {
		envNum := len(newDeployment.Spec.Template.Spec.Containers[i].Env)
		for j := 0; j < envNum; j++ {
			if newDeployment.Spec.Template.Spec.Containers[i].Env[j].Name == "KUBERNETES_SERVICE_HOST" {
				log.Printf("change api to %s\n", s.straggler)
				newDeployment.Spec.Template.Spec.Containers[i].Env[j].Value = s.straggler
				break
			}
		}
	}
	newDeployment, err = clientset.AppsV1().Deployments(s.namespace).Create(context.TODO(), newDeployment, metav1.CreateOptions{})
	checkError(err)
	log.Println(newDeployment.Spec.Template.Spec.Containers[0].Env)

	for true {
		time.Sleep(time.Duration(1) * time.Second)
		pods, err := clientset.CoreV1().Pods(s.namespace).List(context.TODO(), listOptions)
		checkError(err)
		if len(pods.Items) == 0 {
			log.Printf("operator pod not created yet\n")
		} else {
			ready := true
			for i := 0; i < len(pods.Items); i++ {
				if pods.Items[i].Status.Phase == "Running" {
					log.Printf("operator pod %d ready now\n", i)
				} else {
					log.Printf("operator pod %d not ready yet\n", i)
					ready = false
				}
			}
			if ready {
				break
			}
		}
	}
}
