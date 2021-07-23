package main

import (
	"context"
	"log"
	"strings"
	"time"

	appsv1 "k8s.io/api/apps/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
	sonar "sonar.client"
)

func NewAtomicListener(config map[interface{}]interface{}) *AtomicListener {
	server := &atomicServer{
		restarted:   false,
		frontRunner: config["front-runner"].(string),
		deployName:  config["deployment-name"].(string),
		namespace:   "default",
		podLabel:    config["operator-pod-label"].(string),
	}
	listener := &AtomicListener{
		Server: server,
	}
	listener.Server.Start()
	return listener
}

type AtomicListener struct {
	Server *atomicServer
}

func (l *AtomicListener) Echo(request *sonar.EchoRequest, response *sonar.Response) error {
	*response = sonar.Response{Message: "echo " + request.Text, Ok: true}
	return nil
}

func (l *AtomicListener) NotifyAtomicSideEffects(request *sonar.NotifyAtomicSideEffectsRequest, response *sonar.Response) error {
	return l.Server.NotifyAtomicSideEffects(request, response)
}

type atomicServer struct {
	restarted   bool
	frontRunner string
	deployName  string
	namespace   string
	podLabel    string
}

func (s *atomicServer) Start() {
	log.Println("start atomicServer...")
	// go s.coordinatingEvents()
}

func (s *atomicServer) NotifyAtomicSideEffects(request *sonar.NotifyAtomicSideEffectsRequest, response *sonar.Response) error {
	name, namespace := extractNameNamespace(request.Object)
	log.Printf("[SONAR-SIDE-EFFECT]\t%s\t%s\t%s\t%s\t%s\n", request.SideEffectType, request.ResourceType, namespace, name, request.Error)
	if !s.restarted && strings.Contains(request.Stack, "updatePVC") {
		// we should restart operator here
		s.restarted = true
		log.Printf("we restart operator pod here\n")
		s.restartComponent()
		return nil
	}
	*response = sonar.Response{Message: request.SideEffectType, Ok: true}
	return nil
}

func (s *atomicServer) restartComponent() {
	masterUrl := "https://" + s.frontRunner + ":6443"
	config, err := clientcmd.BuildConfigFromFlags(masterUrl, "/root/.kube/config")
	checkError(err)
	clientset, err := kubernetes.NewForConfig(config)
	checkError(err)

	deployment, err := clientset.AppsV1().Deployments(s.namespace).Get(context.TODO(), s.deployName, metav1.GetOptions{})
	checkError(err)
	log.Println(deployment.Spec.Template.Spec.Containers[0].Env)

	clientset.AppsV1().Deployments(s.namespace).Delete(context.TODO(), s.deployName, metav1.DeleteOptions{})

	labelSelector := metav1.LabelSelector{MatchLabels: map[string]string{"sonartag": s.podLabel}}
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
