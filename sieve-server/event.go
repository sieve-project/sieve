package main

import (
	"encoding/json"
	"log"
	"regexp"
	"strings"
)

var seenTargetDiff = false

const TIME_REG string = "^[0-9]+-[0-9]+-[0-9]+T[0-9]+:[0-9]+:[0-9]+Z$"

// mark a list item to skip
const SIEVE_SKIP_MARKER string = "SIEVE-SKIP"

// mark a canonicalized value
const SIEVE_CANONICALIZATION_MARKER string = "SIEVE-NON-NIL"

var exists = struct{}{}

// resources that have different representation between API and controller side
var CONFORM_TYPES = map[string]struct{}{"pod": exists}

// keys that to ignore when computing event diff
var BORING_KEYS = map[string]struct{}{
	"kind":                       exists, // not always available
	"apiVersion":                 exists, // not always available
	"uid":                        exists, // random
	"resourceVersion":            exists, // random
	"generation":                 exists, // random
	"annotations":                exists, // verbose
	"managedFields":              exists, // verbose
	"lastTransitionTime":         exists, // timing
	"deletionGracePeriodSeconds": exists, // timing
	"time":                       exists, // timing
	"podIP":                      exists, // IP assignment is random
	"ip":                         exists, // IP assignment is random
	"hostIP":                     exists, // IP assignment is random
	"nodeName":                   exists, // node assignment is random
	"imageID":                    exists, // image ID is randome
	"ContainerID":                exists, // container ID is random
	"labels":                     exists, // label can contain random strings e.g., controller-revision-hash
}

func inSet(key string, set map[string]struct{}) bool {
	if _, ok := set[key]; ok {
		return true
	} else {
		return false
	}
}

func mapToStr(m map[string]interface{}) string {
	return interfaceToStr(m)
}

func listToStr(l []interface{}) string {
	return interfaceToStr(l)
}

func interfaceToStr(i interface{}) string {
	jsonByte, err := json.Marshal(i)
	if err != nil {
		log.Fatalf("cannot marshal to str: %v\n", i)
	}
	jsonStr := string(jsonByte)
	return jsonStr
}

func mapKeyDiff(mapA, mapB map[string]interface{}) []string {
	diffKeys := make([]string, 0)
	for key := range mapA {
		if _, ok := mapB[key]; !ok {
			diffKeys = append(diffKeys, key)
		}
	}
	return diffKeys
}

func mapKeyIntersection(mapA, mapB map[string]interface{}) []string {
	commonKeys := make([]string, 0)
	for key := range mapA {
		if _, ok := mapB[key]; ok {
			commonKeys = append(commonKeys, key)
		}
	}
	return commonKeys
}

func mapKeySymDiff(mapA, mapB map[string]interface{}) []string {
	diffABKeys := mapKeyDiff(mapA, mapB)
	diffBAKeys := mapKeyDiff(mapB, mapA)
	symDiffKeys := append(diffABKeys, diffBAKeys...)
	return symDiffKeys
}

func diffEventAsList(prevEvent, curEvent []interface{}) ([]interface{}, []interface{}) {
	prevLen := len(prevEvent)
	curLen := len(curEvent)
	minLen := prevLen
	if minLen > curLen {
		minLen = curLen
	}
	diffPrevEvent := make([]interface{}, prevLen)
	diffCurEvent := make([]interface{}, curLen)
	for i := 0; i < prevLen; i++ {
		diffPrevEvent[i] = SIEVE_SKIP_MARKER
	}
	for i := 0; i < curLen; i++ {
		diffCurEvent[i] = SIEVE_SKIP_MARKER
	}
	for i := 0; i < minLen; i++ {
		if interfaceToStr(prevEvent[i]) == interfaceToStr(curEvent[i]) {
			continue
		} else {
			if subCurEvent, ok := curEvent[i].(map[string]interface{}); ok {
				if subPrevEvent, ok := prevEvent[i].(map[string]interface{}); !ok {
					diffPrevEvent[i] = prevEvent[i]
					diffCurEvent[i] = curEvent[i]
				} else {
					subDiffPrevEvent, subDiffCurEvent := diffEventAsMap(subPrevEvent, subCurEvent)
					if len(subDiffPrevEvent) != 0 {
						diffPrevEvent[i] = subDiffPrevEvent
					}
					if len(subDiffCurEvent) != 0 {
						diffCurEvent[i] = subDiffCurEvent
					}
				}
			} else if subCurEvent, ok := curEvent[i].([]interface{}); ok {
				if subPrevEvent, ok := prevEvent[i].([]interface{}); !ok {
					diffPrevEvent[i] = prevEvent[i]
					diffCurEvent[i] = curEvent[i]
				} else {
					subDiffPrevEvent, subDiffCurEvent := diffEventAsList(subPrevEvent, subCurEvent)
					if len(subDiffPrevEvent) != 0 {
						diffPrevEvent[i] = subDiffPrevEvent
					}
					if len(subDiffCurEvent) != 0 {
						diffCurEvent[i] = subDiffCurEvent
					}
				}
			} else {
				diffPrevEvent[i] = prevEvent[i]
				diffCurEvent[i] = curEvent[i]
			}
		}
	}
	keepDiffPrev := false
	for i := 0; i < prevLen; i++ {
		if val, ok := diffPrevEvent[i].(string); ok {
			if val != SIEVE_SKIP_MARKER {
				keepDiffPrev = true
			}
		} else {
			keepDiffPrev = true
		}
	}
	keepDiffCur := false
	for i := 0; i < curLen; i++ {
		if val, ok := diffCurEvent[i].(string); ok {
			if val != SIEVE_SKIP_MARKER {
				keepDiffCur = true
			}
		} else {
			keepDiffCur = true
		}
	}
	if !keepDiffPrev {
		diffPrevEvent = nil
	}
	if !keepDiffCur {
		diffCurEvent = nil
	}
	return diffPrevEvent, diffCurEvent
}

func diffEventAsMap(prevEvent, curEvent map[string]interface{}) (map[string]interface{}, map[string]interface{}) {
	diffPrevEvent := make(map[string]interface{})
	diffCurEvent := make(map[string]interface{})
	for _, key := range mapKeyIntersection(prevEvent, curEvent) {
		if inSet(key, BORING_KEYS) {
			continue
		} else if interfaceToStr(prevEvent[key]) == interfaceToStr(curEvent[key]) {
			continue
		} else {
			if subCurEvent, ok := curEvent[key].(map[string]interface{}); ok {
				if subPrevEvent, ok := prevEvent[key].(map[string]interface{}); !ok {
					diffPrevEvent[key] = prevEvent[key]
					diffCurEvent[key] = curEvent[key]
				} else {
					subDiffPrevEvent, subDiffCurEvent := diffEventAsMap(subPrevEvent, subCurEvent)
					if len(subDiffPrevEvent) != 0 {
						diffPrevEvent[key] = subDiffPrevEvent
					}
					if len(subDiffCurEvent) != 0 {
						diffCurEvent[key] = subDiffCurEvent
					}
				}
			} else if subCurEvent, ok := curEvent[key].([]interface{}); ok {
				if subPrevEvent, ok := prevEvent[key].([]interface{}); !ok {
					diffPrevEvent[key] = prevEvent[key]
					diffCurEvent[key] = curEvent[key]
				} else {
					subDiffPrevEvent, subDiffCurEvent := diffEventAsList(subPrevEvent, subCurEvent)
					if len(subDiffPrevEvent) != 0 {
						diffPrevEvent[key] = subDiffPrevEvent
					}
					if len(subDiffCurEvent) != 0 {
						diffCurEvent[key] = subDiffCurEvent
					}
				}
			} else {
				diffPrevEvent[key] = prevEvent[key]
				diffCurEvent[key] = curEvent[key]
			}
		}
	}
	for _, key := range mapKeyDiff(prevEvent, curEvent) {
		if inSet(key, BORING_KEYS) {
			continue
		}
		diffPrevEvent[key] = prevEvent[key]
	}
	for _, key := range mapKeyDiff(curEvent, prevEvent) {
		if inSet(key, BORING_KEYS) {
			continue
		}
		diffCurEvent[key] = curEvent[key]
	}
	return diffPrevEvent, diffCurEvent
}

func canonicalizeValue(value string) string {
	match, err := regexp.MatchString(TIME_REG, value)
	if err != nil {
		log.Fatalf("fail to compile %s", TIME_REG)
	}
	if match {
		return SIEVE_CANONICALIZATION_MARKER
	} else {
		return value
	}
}

func canonicalizeEventAsList(event []interface{}) {
	for i, val := range event {
		switch typedVal := val.(type) {
		case map[string]interface{}:
			canonicalizeEventAsMap(typedVal)
		case []interface{}:
			canonicalizeEventAsList(typedVal)
		case string:
			event[i] = canonicalizeValue(typedVal)
		}
	}
}

func canonicalizeEventAsMap(event map[string]interface{}) {
	for key, val := range event {
		switch typedVal := val.(type) {
		case map[string]interface{}:
			canonicalizeEventAsMap(typedVal)
		case []interface{}:
			canonicalizeEventAsList(typedVal)
		case string:
			event[key] = canonicalizeValue(typedVal)
		}
	}
}

func diffEvent(prevEvent, curEvent map[string]interface{}) (map[string]interface{}, map[string]interface{}) {
	// We first compute the diff between the prevEvent and the curEvent
	diffPrevEvent, diffCurEvent := diffEventAsMap(prevEvent, curEvent)
	// Deepcopy the diff[Prev|Cur]Event as we need to modify them during canonicalization
	copiedDiffPrevEvent := deepCopyMap(diffPrevEvent)
	copiedDiffCurEvent := deepCopyMap(diffCurEvent)
	// We canonicalize all the timing related fields
	canonicalizeEventAsMap(copiedDiffPrevEvent)
	canonicalizeEventAsMap(copiedDiffCurEvent)
	// After canonicalization some values are replaced by SIEVE_CANONICALIZATION_MARKER, we compute diff again
	diffPrevEventAfterCan, diffCurEventAfterCan := diffEventAsMap(copiedDiffPrevEvent, copiedDiffCurEvent)
	// Note that we do not perform canonicalization at the beginning as it is more expensive to do so
	return diffPrevEventAfterCan, diffCurEventAfterCan
}

func equivalentEvent(eventA, eventB map[string]interface{}) bool {
	return mapToStr(eventA) == mapToStr(eventB)
}

func partOfEventAsList(eventA, eventB []interface{}) bool {
	if len(eventA) != len(eventB) {
		return false
	}
	for i, valA := range eventA {
		valB := eventB[i]
		if interfaceToStr(valA) == interfaceToStr(valB) {
			continue
		}
		switch typedValA := valA.(type) {
		case map[string]interface{}:
			if typedValB, ok := eventB[i].(map[string]interface{}); ok {
				if !partOfEventAsMap(typedValA, typedValB) {
					return false
				}
			} else {
				return false
			}
		case []interface{}:
			if typedValB, ok := eventB[i].([]interface{}); ok {
				if !partOfEventAsList(typedValA, typedValB) {
					return false
				}
			} else {
				return false
			}
		case string:
			if typedValA != SIEVE_CANONICALIZATION_MARKER && typedValA != SIEVE_SKIP_MARKER {
				return false
			}
		default:
			return false
		}
	}
	return true
}

func partOfEventAsMap(eventA, eventB map[string]interface{}) bool {
	for key := range eventA {
		if _, ok := eventB[key]; !ok {
			return false
		}
	}
	for key, valA := range eventA {
		valB := eventB[key]
		if interfaceToStr(valA) == interfaceToStr(valB) {
			continue
		}
		switch typedValA := valA.(type) {
		case map[string]interface{}:
			if typedValB, ok := eventB[key].(map[string]interface{}); ok {
				if !partOfEventAsMap(typedValA, typedValB) {
					return false
				}
			} else {
				return false
			}
		case []interface{}:
			if typedValB, ok := eventB[key].([]interface{}); ok {
				if !partOfEventAsList(typedValA, typedValB) {
					return false
				}
			} else {
				return false
			}
		case string:
			if typedValA != SIEVE_CANONICALIZATION_MARKER {
				return false
			}
		default:
			return false
		}
	}
	return true
}

func conflictingEventAsMap(eventA, eventB map[string]interface{}) bool {
	return !partOfEventAsMap(eventA, eventB)
}

func findTargetDiff(prevEvent, curEvent, targetDiffPrevEvent, targetDiffCurEvent map[string]interface{}, forgiving bool) bool {
	if seenTargetDiff {
		return false
	}
	if prevEvent == nil || curEvent == nil || targetDiffPrevEvent == nil || targetDiffCurEvent == nil {
		return false
	}
	onlineDiffPrevEvent, onlineDiffCurEvent := diffEvent(prevEvent, curEvent)
	log.Printf("online diff: prev: %s\n", mapToStr(onlineDiffPrevEvent))
	log.Printf("online diff: cur: %s\n", mapToStr(onlineDiffCurEvent))
	if equivalentEvent(onlineDiffPrevEvent, targetDiffPrevEvent) && equivalentEvent(onlineDiffCurEvent, targetDiffCurEvent) {
		log.Println("Find the target diff")
		seenTargetDiff = true
		return true
	} else if forgiving {
		if partOfEventAsMap(targetDiffPrevEvent, onlineDiffPrevEvent) && partOfEventAsMap(targetDiffCurEvent, onlineDiffCurEvent) {
			log.Println("Find the target diff by being forgiving")
			seenTargetDiff = true
			return true
		}
	}
	return false
}

func capitalizeKey(key string) string {
	return strings.ToUpper(key[0:1]) + key[1:]
}

func capitalizeEventAsList(event []interface{}) []interface{} {
	capitalizedEvent := make([]interface{}, len(event))
	for i, val := range event {
		switch typedVal := val.(type) {
		case map[string]interface{}:
			capitalizedEvent[i] = capitalizeEventAsMap(typedVal)
		case []interface{}:
			capitalizedEvent[i] = capitalizeEventAsList(typedVal)
		default:
			capitalizedEvent[i] = typedVal
		}
	}
	return capitalizedEvent
}

func capitalizeEventAsMap(event map[string]interface{}) map[string]interface{} {
	capitalizedEvent := make(map[string]interface{})
	for key, val := range event {
		switch typedVal := val.(type) {
		case map[string]interface{}:
			capitalizedEvent[capitalizeKey(key)] = capitalizeEventAsMap(typedVal)
		case []interface{}:
			capitalizedEvent[capitalizeKey(key)] = capitalizeEventAsList(typedVal)
		default:
			capitalizedEvent[capitalizeKey(key)] = typedVal
		}
	}
	return capitalizedEvent
}

func conformToAPIEvent(event map[string]interface{}, rType string) map[string]interface{} {
	if !inSet(rType, CONFORM_TYPES) {
		return event
	}

	log.Println("Need to conform")

	// Sometimes the event object representation is different between the API side and the operator side
	// There are mainly two difference:
	// 1. `metadata` is missing at the API side but the inner fields still exist
	// 2. field name starts with a capitalized word if not inside `metadata` at the API side
	conformedEvent := make(map[string]interface{})

	// step 1: move any field inside `metadata` outside
	if val, ok := event["metadata"]; ok {
		metadataMap := val.(map[string]interface{})
		for mkey, mval := range metadataMap {
			conformedEvent[mkey] = mval
		}
		delete(event, "metadata")
	}

	// step 2: capitalized each key if it is not in `metadata`
	capitalizedEvent := capitalizeEventAsMap(event)
	for key, val := range capitalizedEvent {
		conformedEvent[key] = val
	}

	return conformedEvent
}
