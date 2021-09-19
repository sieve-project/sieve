package main

import (
	"encoding/json"
	"io/ioutil"
	"log"
	"reflect"
	"strings"

	"gopkg.in/yaml.v2"
)

const TIME_TRAVEL string = "time-travel"
const OBS_GAP string = "observability-gap"
const ATOM_VIO string = "atomicity-violation"
const TEST string = "test"
const LEARN string = "learn"

// type eventWrapper struct {
// 	eventID         int32
// 	eventType       string
// 	eventObject     string
// 	eventObjectType string
// }

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

func getEventResourceName(event map[string]interface{}) string {
	if event["metadata"] != nil {
		metadata := event["metadata"].(map[string]interface{})
		return metadata["name"].(string)
	} else {
		return event["name"].(string)
	}
}

func getEventResourceNamespace(event map[string]interface{}) string {
	if event["metadata"] != nil {
		metadata := event["metadata"].(map[string]interface{})
		return metadata["namespace"].(string)
	} else {
		return event["namespace"].(string)
	}
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

func isSameObject(currentEvent map[string]interface{}, namespace string, name string) bool {
	return getEventResourceNamespace(currentEvent) == namespace && getEventResourceName(currentEvent) == name
}
