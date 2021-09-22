package main

import (
	"context"
	"encoding/json"
	"io/ioutil"
	"log"
	"reflect"
	"strings"
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

func toLowerMap(m map[string]interface{}) {
	for key, val := range m {
		switch v := val.(type) {
		case map[string]interface{}:
			if e, ok := m[key].(map[string]interface{}); ok {
				toLowerMap(e)
				if strings.ToLower(key) != key {
					m[strings.ToLower(key)] = e
					delete(m, key)
				}
			} else {
				log.Println("m[key] assertion to map[string]interface{} fail")
			}

		case []interface{}:
			if e, ok := m[key].([]interface{}); ok {
				for idx := range e {
					switch e[idx].(type) {
					case map[string]interface{}:
						if eSlice, ok := e[idx].(map[string]interface{}); ok {
							toLowerMap(eSlice)
						}
					case []interface{}:
						log.Println("toLowerMap does not support slice in slice for now")
					}
				}
				if strings.ToLower(key) != key {
					m[strings.ToLower(key)] = e
					delete(m, key)
				}
			} else {
				log.Println("m[key] assertion to []interface{} fail")
			}

		default:
			m[strings.ToLower(key)] = v
			if strings.ToLower(key) != key {
				delete(m, key)
			}

		}
	}
}

func strToMap(str string) map[string]interface{} {
	m := make(map[string]interface{})
	err := json.Unmarshal([]byte(str), &m)
	if err != nil {
		log.Fatalf("cannot unmarshal to map: %s\n", str)
	}
	toLowerMap(m)
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
			if v == "SIEVE-NON-NIL" || v == "SIEVE-SKIP" {
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
			log.Println("Match fail", key, val, "currentEvent keys", reflect.ValueOf(currentEvent).MapKeys())
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
			if v == "SIEVE-NON-NIL" {
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
			if e, ok := currentEvent[key]; ok {
				if val == nil && e == nil {
					log.Printf("Both nil type: %v and %v , key: %s\n", v, e, key)
					return true
				}
			}

			log.Printf("Unsupported type: %v %T, key: %s\n", v, v, key)
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

func seenCrucialEvent(seenPrev, seenCur *bool, crucialCurEvent, crucialPrevEvent, currentEvent map[string]interface{}) bool {
	if !*seenCur {
		if !*seenPrev {
			if isCrucial(crucialPrevEvent, currentEvent) && (len(crucialCurEvent) == 0 || !isCrucial(crucialCurEvent, currentEvent)) {
				log.Println("Meet crucialPrevEvent: set seenPrev to true")
				*seenPrev = true
				return false
			}
		} else {
			if isCrucial(crucialCurEvent, currentEvent) && (len(crucialPrevEvent) == 0 || !isCrucial(crucialPrevEvent, currentEvent)) {
				log.Println("Meet crucialCurEvent: set seenCur to true")
				*seenCur = true
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

func cancelEventList(crucialEvent, currentEvent []interface{}) bool {
	if len(currentEvent) < len(crucialEvent) {
		return true
	}
	for i, val := range crucialEvent {
		switch v := val.(type) {
		case int64:
			if e, ok := currentEvent[i].(int64); ok {
				if v != e {
					log.Println("cancel event", v, e)
					return true
				}
			}
		case float64:
			if e, ok := currentEvent[i].(float64); ok {
				if v != e {
					log.Println("cancel event", v, e)
					return true
				}
			}
		case bool:
			if e, ok := currentEvent[i].(bool); ok {
				if v != e {
					log.Println("cancel event", v, e)
					return true
				}
			}
		case string:
			if v == "SIEVE-NON-NIL" || v == "SIEVE-SKIP" {
				continue
			} else if e, ok := currentEvent[i].(string); ok {
				if v != e {
					log.Println("cancel event", v, e)
					return true
				}
			}
		case map[string]interface{}:
			if e, ok := currentEvent[i].(map[string]interface{}); ok {
				if cancelEvent(v, e) {
					log.Println("cancel event", v, e)
					return true
				}
			}
		default:
			log.Printf("Unsupported type: %v %T\n", v, v)
		}
	}
	return false
}

func cancelEvent(crucialEvent, currentEvent map[string]interface{}) bool {
	for key, val := range crucialEvent {
		if _, ok := currentEvent[key]; !ok {
			log.Println("cancel event, not exist", key)
			return true
		}
		switch v := val.(type) {
		case int64:
			if e, ok := currentEvent[key].(int64); ok {
				if v != e {
					log.Println("cancel event", key)
					return true
				}
			}
		case float64:
			if e, ok := currentEvent[key].(float64); ok {
				if v != e {
					log.Println("cancel event", key)
					return true
				}
			}
		case bool:
			if e, ok := currentEvent[key].(bool); ok {
				if v != e {
					log.Println("cancel event", key)
					return true
				}
			}
		case string:
			if v == "SIEVE-NON-NIL" {
				continue
			} else if e, ok := currentEvent[key].(string); ok {
				if v != e {
					log.Println("cancel event", key)
					return true
				}
			}
		case map[string]interface{}:
			if e, ok := currentEvent[key].(map[string]interface{}); ok {
				if cancelEvent(v, e) {
					log.Println("cancel event", key)
					return true
				}
			}
		case []interface{}:
			if e, ok := currentEvent[key].([]interface{}); ok {
				if cancelEventList(v, e) {
					log.Println("cancel event", key)
					return true
				}
			}

		default:
			log.Printf("Unsupported type: %v %T, key: %s\n", v, v, key)
		}
	}
	return false
}

func extractNameNamespaceFromObjString(objStr string) (string, string) {
	objMap := strToMap(objStr)
	return extractNameNamespaceFromObjMap(objMap)
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

// func getEventResourceName(event map[string]interface{}) string {
// 	if event["metadata"] != nil {
// 		metadata := event["metadata"].(map[string]interface{})
// 		return metadata["name"].(string)
// 	} else {
// 		return event["name"].(string)
// 	}
// }

// func getEventResourceNamespace(event map[string]interface{}) string {
// 	if event["metadata"] != nil {
// 		metadata := event["metadata"].(map[string]interface{})
// 		return metadata["namespace"].(string)
// 	} else {
// 		return event["namespace"].(string)
// 	}
// }

func isSameObject(currentEvent map[string]interface{}, namespace string, name string) bool {
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
