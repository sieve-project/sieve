package main

import (
	"context"
	"encoding/json"
	"io/ioutil"
	"log"
	"time"

	"gopkg.in/yaml.v2"
	appsv1 "k8s.io/api/apps/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/labels"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/clientcmd"
)

func checkError(err error) {
	if err != nil {
		log.Fatalf("Fail due to error: %v\n", err)
	}
}

func getConfig() map[interface{}]interface{} {

	data, err := ioutil.ReadFile("server.yaml")
	checkError(err)
	m := make(map[interface{}]interface{})

	err = yaml.Unmarshal([]byte(data), &m)
	checkError(err)
	log.Printf("config:\n%v\n", m)

	return m
}

func strToMap(str string) map[string]interface{} {
	m := make(map[string]interface{})
	err := json.Unmarshal([]byte(str), &m)
	if err != nil {
		log.Fatalf("cannot unmarshal to map: %s\n", str)
	}
	return m
}

func deepCopyMap(src map[string]interface{}) map[string]interface{} {
	dest := make(map[string]interface{})
	if src == nil {
		log.Fatalf("src is nil. You cannot read from a nil map")
	}
	jsonStr, err := json.Marshal(src)
	if err != nil {
		log.Fatalf(err.Error())
	}
	err = json.Unmarshal(jsonStr, &dest)
	if err != nil {
		log.Fatalf(err.Error())
	}
	return dest
}

func startTimeTravelInjection() {
	log.Println("START-SIEVE-TIME-TRAVEL")
}

func startObsGapInjection() {
	log.Println("START-SIEVE-OBSERVABILITY-GAPS")
}

func startAtomVioInjection() {
	log.Println("START-SIEVE-ATOMICITY-VIOLATION")
}

func finishTimeTravelInjection() {
	log.Println("FINISH-SIEVE-TIME-TRAVEL")
}

func finishObsGapInjection() {
	log.Println("FINISH-SIEVE-OBSERVABILITY-GAPS")
}

func finishAtomVioInjection() {
	log.Println("FINISH-SIEVE-ATOMICITY-VIOLATION")
}

func extractNameNamespaceFromObjMap(objMap map[string]interface{}) (string, string) {
	name := ""
	namespace := ""
	if _, ok := objMap["metadata"]; ok {
		if metadataMap, ok := objMap["metadata"].(map[string]interface{}); ok {
			if _, ok := metadataMap["name"]; ok {
				name = metadataMap["name"].(string)
			}
			if _, ok := metadataMap["namespace"]; ok {
				namespace = metadataMap["namespace"].(string)
			}
		}
	} else {
		if _, ok := objMap["name"]; ok {
			name = objMap["name"].(string)
		}
		if _, ok := objMap["namespace"]; ok {
			namespace = objMap["namespace"].(string)
		}
	}
	return name, namespace
}

func isSameObjectServerSide(currentEvent map[string]interface{}, namespace string, name string) bool {
	extractedName, extractedNamespace := extractNameNamespaceFromObjMap(currentEvent)
	return extractedNamespace == namespace && extractedName == name
}

func restartOperator(namespace, deployName, podLabel, leadingAPI, followingAPI string, redirect bool) {
	masterUrl := "https://" + leadingAPI + ":6443"
	config, err := clientcmd.BuildConfigFromFlags(masterUrl, "/root/.kube/config")
	checkError(err)
	clientset, err := kubernetes.NewForConfig(config)
	checkError(err)

	deployment, err := clientset.AppsV1().Deployments(namespace).Get(context.TODO(), deployName, metav1.GetOptions{})
	checkError(err)
	log.Println(deployment.Spec.Template.Spec.Containers[0].Env)

	clientset.AppsV1().Deployments(namespace).Delete(context.TODO(), deployName, metav1.DeleteOptions{})

	labelSelector := metav1.LabelSelector{MatchLabels: map[string]string{"sievetag": podLabel}}
	listOptions := metav1.ListOptions{
		LabelSelector: labels.Set(labelSelector.MatchLabels).String(),
	}

	for {
		time.Sleep(time.Duration(1) * time.Second)
		pods, err := clientset.CoreV1().Pods(namespace).List(context.TODO(), listOptions)
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

	if redirect {
		containersNum := len(newDeployment.Spec.Template.Spec.Containers)
		for i := 0; i < containersNum; i++ {
			envNum := len(newDeployment.Spec.Template.Spec.Containers[i].Env)
			for j := 0; j < envNum; j++ {
				if newDeployment.Spec.Template.Spec.Containers[i].Env[j].Name == "KUBERNETES_SERVICE_HOST" {
					log.Printf("change api to %s\n", followingAPI)
					newDeployment.Spec.Template.Spec.Containers[i].Env[j].Value = followingAPI
					break
				}
			}
		}
	}

	newDeployment, err = clientset.AppsV1().Deployments(namespace).Create(context.TODO(), newDeployment, metav1.CreateOptions{})
	checkError(err)
	log.Println(newDeployment.Spec.Template.Spec.Containers[0].Env)

	for {
		time.Sleep(time.Duration(1) * time.Second)
		pods, err := clientset.CoreV1().Pods(namespace).List(context.TODO(), listOptions)
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
