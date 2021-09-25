package main

import (
	"encoding/json"
	"log"
	"regexp"
)

const TIME_REG string = "^[0-9]+-[0-9]+-[0-9]+T[0-9]+:[0-9]+:[0-9]+Z$"

const SIEVE_SKIP_MARKER string = "SIEVE-SKIP"
const SIEVE_CANONICALIZATION_MARKER string = "SIEVE-NON-NIL"

var BORING_KEYS = [...]string{
	"uid",                        // random
	"resourceVersion",            // random
	"generation",                 // random
	"annotations",                // verbose
	"managedFields",              // verbose
	"lastTransitionTime",         // timing
	"deletionGracePeriodSeconds", // timing
	"time",                       // timing
	"podIP",                      // IP assignment is random
	"ip",                         // IP assignment is random
	"hostIP",                     // IP assignment is random
	"nodeName",                   // node assignment is random
	"imageID",                    // image ID is randome
	"ContainerID",                // container ID is random
	"labels",                     // label can contain random strings e.g., controller-revision-hash
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

func boringKey(key string) bool {
	for _, bKey := range BORING_KEYS {
		if key == bKey {
			return true
		}
	}
	return false
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
		if boringKey(key) {
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
		if boringKey(key) {
			continue
		}
		diffPrevEvent[key] = prevEvent[key]
	}
	for _, key := range mapKeyDiff(curEvent, prevEvent) {
		if boringKey(key) {
			continue
		}
		diffCurEvent[key] = curEvent[key]
	}
	return diffPrevEvent, diffCurEvent
}

func diffEvent(prevEvent, curEvent map[string]interface{}) (map[string]interface{}, map[string]interface{}) {
	diffPrevEvent, diffCurEvent := diffEventAsMap(prevEvent, curEvent)
	copiedDiffPrevEvent := deepCopyMap(diffPrevEvent)
	copiedDiffCurEvent := deepCopyMap(diffCurEvent)
	canonicalizeEventAsMap(copiedDiffPrevEvent)
	canonicalizeEventAsMap(copiedDiffCurEvent)
	return copiedDiffPrevEvent, copiedDiffCurEvent
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

func equivalentEvent(eventA, eventB map[string]interface{}) bool {
	return mapToStr(eventA) == mapToStr(eventB)
}

func seenCrucialEventV2(prevEvent, curEvent, targetDiffPrevEvent, targetDiffCurEvent map[string]interface{}) bool {
	if prevEvent == nil || curEvent == nil || targetDiffPrevEvent == nil || targetDiffCurEvent == nil {
		return false
	}
	onlineDiffPrevEvent, onlineDiffCurEvent := diffEvent(prevEvent, curEvent)
	log.Printf("online delta: prev: %s\n", mapToStr(onlineDiffPrevEvent))
	log.Printf("online delta: cur: %s\n", mapToStr(onlineDiffCurEvent))
	if equivalentEvent(onlineDiffPrevEvent, targetDiffPrevEvent) && equivalentEvent(onlineDiffCurEvent, targetDiffCurEvent) {
		log.Println("Find the crucial event")
		return true
	} else {
		return false
	}
}
