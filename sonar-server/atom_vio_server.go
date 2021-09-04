package main

import (
	"context"
	"log"
	"sync/atomic"
	"time"

	appsv1 "k8s.io/api/apps/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
	sonar "sieve.client"
)

func NewAtomVioListener(config map[interface{}]interface{}) *AtomVioListener {
	server := &atomVioServer{
		restarted:   false,
		crash:       false,
		seenPrev:    false,
		eventID:     -1,
		frontRunner: config["front-runner"].(string),
		deployName:  config["deployment-name"].(string),
		namespace:   "default",
		podLabel:    config["operator-pod-label"].(string),
		crucialCur:  config["ce-diff-current"].(string),
		crucialPrev: config["ce-diff-previous"].(string),
		ceName:      config["ce-name"].(string),
		ceNamespace: config["ce-namespace"].(string),
		ceRtype:     config["ce-rtype"].(string),
		seName:      config["se-name"].(string),
		seNamespace: config["se-namespace"].(string),
		seRtype:     config["se-rtype"].(string),
		seEtype:     config["se-etype"].(string),
	}
	listener := &AtomVioListener{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

type AtomVioListener struct {
	Server *atomVioServer
}

func (l *AtomVioListener) Echo(request *sonar.EchoRequest, response *sonar.Response) error {
	*response = sonar.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *AtomVioListener) NotifyAtomVioSideEffects(request *sonar.NotifyAtomVioSideEffectsRequest, response *sonar.Response) error {
	return l.Server.NotifyAtomVioSideEffects(request, response)
}

func (l *AtomVioListener) NotifyAtomVioBeforeIndexerWrite(request *sonar.NotifyAtomVioBeforeIndexerWriteRequest, response *sonar.Response) error {
	return l.Server.NotifyAtomVioBeforeIndexerWrite(request, response)
}

type atomVioServer struct {
	restarted    bool
	frontRunner  string
	deployName   string
	namespace    string
	podLabel     string
	crucialCur   string
	crucialPrev  string
	ceName       string
	ceNamespace  string
	ceRtype      string
	crucialEvent eventWrapper
	eventID      int32
	seenPrev     bool
	crash        bool
	seName       string
	seNamespace  string
	seRtype      string
	seEtype      string
}

func (s *atomVioServer) Start() {
	log.Println("start atomicServer...")
	// go s.coordinatingEvents()
}

func (s *atomVioServer) shouldCrash(crucialCurEvent, crucialPrevEvent, currentEvent map[string]interface{}) bool {
	if !s.crash {
		if !s.seenPrev {
			if isCrucial(crucialPrevEvent, currentEvent) && (len(crucialCurEvent) == 0 || !isCrucial(crucialCurEvent, currentEvent)) {
				log.Println("Meet crucialPrevEvent: set seenPrev to true")
				s.seenPrev = true
			}
		} else {
			if isCrucial(crucialCurEvent, currentEvent) && (len(crucialPrevEvent) == 0 || !isCrucial(crucialPrevEvent, currentEvent)) {
				log.Println("Meet crucialCurEvent: set paused to true and start to pause")
				s.crash = true
				return true
			}
		}
	}
	return false
}

// For now, we get an cruial event from API server, we want to see if any later event cancel this one
func (s *atomVioServer) NotifyAtomVioBeforeIndexerWrite(request *sonar.NotifyAtomVioBeforeIndexerWriteRequest, response *sonar.Response) error {
	eID := atomic.AddInt32(&s.eventID, 1)
	ew := eventWrapper{
		eventID:         eID,
		eventType:       request.OperationType,
		eventObject:     request.Object,
		eventObjectType: request.ResourceType,
	}
	log.Println("NotifyAtomVioBeforeIndexerWrite", ew.eventID, ew.eventType, ew.eventObjectType, ew.eventObject)
	currentEvent := strToMap(request.Object)
	crucialCurEvent := strToMap(s.crucialCur)
	crucialPrevEvent := strToMap(s.crucialPrev)
	// We then check for the crucial event
	if ew.eventObjectType == s.ceRtype && getEventResourceName(currentEvent) == s.ceName && getEventResourceNamespace(currentEvent) == s.ceNamespace {
		log.Print("[sonar] we then check for crash condition", "s.crash", s.crash, "s.seenPrev", s.seenPrev)
		if s.shouldCrash(crucialCurEvent, crucialPrevEvent, currentEvent) {
			log.Println("[sonar] should crash the operator while issuing target side effect")
			s.crucialEvent = ew
		}
	}
	*response = sonar.Response{Message: request.OperationType, Ok: true, Number: int(eID)}
	return nil
}

func (s *atomVioServer) NotifyAtomVioSideEffects(request *sonar.NotifyAtomVioSideEffectsRequest, response *sonar.Response) error {
	name, namespace := extractNameNamespace(request.Object)
	log.Printf("[SONAR-SIDE-EFFECT]\t%s\t%s\t%s\t%s\t%s\n", request.SideEffectType, request.ResourceType, namespace, name, request.Error)
	if s.crash && !s.restarted && request.ResourceType == s.seRtype && request.SideEffectType == s.seEtype && name == s.seName && namespace == s.seNamespace {
		// we should restart operator here
		s.restarted = true
		log.Printf("we restart operator pod here\n")
		s.restartComponent()
		return nil
	}
	*response = sonar.Response{Message: request.SideEffectType, Ok: true}
	return nil
}

func (s *atomVioServer) restartComponent() {
	masterUrl := "https://" + s.frontRunner + ":6443"
	config, err := clientcmd.BuildConfigFromFlags(masterUrl, "/root/.kube/config")
	checkError(err)
	clientset, err := kubernetes.NewForConfig(config)
	checkError(err)

	deployment, err := clientset.AppsV1().Deployments(s.namespace).Get(context.TODO(), s.deployName, metav1.GetOptions{})
	checkError(err)
	log.Println(deployment.Spec.Template.Spec.Containers[0].Env)

	clientset.AppsV1().Deployments(s.namespace).Delete(context.TODO(), s.deployName, metav1.DeleteOptions{})

	labelSelector := metav1.LabelSelector{MatchLabels: map[string]string{"sievetag": s.podLabel}}
	listOptions := metav1.ListOptions{
		LabelSelector: labels.Set(labelSelector.MatchLabels).String(),
	}

	for {
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

	newDeployment, err = clientset.AppsV1().Deployments(s.namespace).Create(context.TODO(), newDeployment, metav1.CreateOptions{})
	checkError(err)
	log.Println(newDeployment.Spec.Template.Spec.Containers[0].Env)

	for {
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
