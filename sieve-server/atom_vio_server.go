package main

import (
	"context"
	"log"
	"time"

	appsv1 "k8s.io/api/apps/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
	sieve "sieve.client"
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
		seName:      config["se-name"].(string),
		seNamespace: config["se-namespace"].(string),
		seRtype:     config["se-rtype"].(string),
		seEtype:     config["se-etype"].(string),
		crucialCur:  config["se-diff-current"].(string),
		crucialPrev: config["se-diff-previous"].(string),
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

func (l *AtomVioListener) Echo(request *sieve.EchoRequest, response *sieve.Response) error {
	*response = sieve.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *AtomVioListener) NotifyAtomVioAfterOperatorGet(request *sieve.NotifyAtomVioAfterOperatorGetRequest, response *sieve.Response) error {
	return l.Server.NotifyAtomVioAfterOperatorGet(request, response)
}

func (l *AtomVioListener) NotifyAtomVioAfterOperatorList(request *sieve.NotifyAtomVioAfterOperatorListRequest, response *sieve.Response) error {
	return l.Server.NotifyAtomVioAfterOperatorList(request, response)
}

func (l *AtomVioListener) NotifyAtomVioAfterSideEffects(request *sieve.NotifyAtomVioAfterSideEffectsRequest, response *sieve.Response) error {
	return l.Server.NotifyAtomVioAfterSideEffects(request, response)
}

type atomVioServer struct {
	restarted   bool
	frontRunner string
	deployName  string
	namespace   string
	podLabel    string
	eventID     int32
	seenPrev    bool
	crash       bool
	seName      string
	seNamespace string
	seRtype     string
	seEtype     string
	crucialCur  string
	crucialPrev string
}

func (s *atomVioServer) Start() {
	log.Println("start atomVioServer...")
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

func (s *atomVioServer) NotifyAtomVioAfterOperatorGet(request *sieve.NotifyAtomVioAfterOperatorGetRequest, response *sieve.Response) error {
	log.Printf("[SIEVE-AFTER-READ]\tGet\t%s\t%s\t%s\t%s\t%s", request.ResourceType, request.Namespace, request.Name, request.Error, request.Object)
	if request.Error == "NoError" {
		readObj := strToMap(request.Object)
		crucialCurEvent := strToMap(s.crucialCur)
		crucialPrevEvent := strToMap(s.crucialPrev)
		if request.ResourceType == s.seRtype && isSameObject(readObj, s.seNamespace, s.seName) {
			if !s.seenPrev {
				s.shouldCrash(crucialCurEvent, crucialPrevEvent, readObj)
			}
		}
	}
	*response = sieve.Response{Message: request.ResourceType, Ok: true}
	return nil
}

func (s *atomVioServer) NotifyAtomVioAfterOperatorList(request *sieve.NotifyAtomVioAfterOperatorListRequest, response *sieve.Response) error {
	log.Printf("[SIEVE-AFTER-READ]\tList\t%s\t%s\t%s", request.ResourceType, request.Error, request.ObjectList)

	*response = sieve.Response{Message: request.ResourceType, Ok: true}
	return nil
}

func (s *atomVioServer) NotifyAtomVioAfterSideEffects(request *sieve.NotifyAtomVioAfterSideEffectsRequest, response *sieve.Response) error {
	log.Printf("[SIEVE-AFTER-SIDE-EFFECT]\t%d\t%s\t%s\t%s\t%s\n", -1, request.SideEffectType, request.ResourceType, request.Error, request.Object)

	writeObj := strToMap(request.Object)
	crucialCurEvent := strToMap(s.crucialCur)
	crucialPrevEvent := strToMap(s.crucialPrev)
	if request.ResourceType == s.seRtype && isSameObject(writeObj, s.seNamespace, s.seName) && request.SideEffectType == s.seEtype {
		if s.seenPrev {
			if s.shouldCrash(crucialCurEvent, crucialPrevEvent, writeObj) {
				log.Println("ready to crash!")
				s.restartComponent()
			}
		}
	}
	*response = sieve.Response{Message: request.SideEffectType, Ok: true}
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
