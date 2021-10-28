package main

import (
	"encoding/json"
	"log"
	"path"
	"reflect"
	"regexp"
	"strings"
	"sync"
)

var seenTargetCounter = 0
var findTargetDiffMutex = &sync.Mutex{}

const TIME_REG string = `^[0-9]+-[0-9]+-[0-9]+T[0-9]+:[0-9]+:[0-9]+Z$`
const IP_REG string = `^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$`

var MASK_REGS = []string{TIME_REG, IP_REG}

// mark a list item to skip
const SIEVE_IDX_SKIP string = "SIEVE-SKIP"

// mark a canonicalized value
const SIEVE_VALUE_MASK string = "SIEVE-NON-NIL"

const SIEVE_CAN_MARKER string = "SIEVE-CAN"

const (
	HEAR_ADDED    string = "Added"
	HEAR_UPDATED  string = "Updated"
	HEAR_DELETED  string = "Deleted"
	HEAR_REPLACED string = "Replaced"
	HEAR_SYNC     string = "Sync"
	API_ADDED     string = "ADDED"
	API_MODIFIED  string = "MODIFIED"
	API_DELETED   string = "DELETED"
	WRITE_CREATE  string = "Create"
	WRITE_UPDATE  string = "Update"
	WRITE_DELETE  string = "Delete"
	WRITE_PATCH   string = "Patch"
)

var exists = struct{}{}

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
	// We initialize both lists with SIEVE_IDX_SKIP
	for i := 0; i < prevLen; i++ {
		diffPrevEvent[i] = SIEVE_IDX_SKIP
	}
	for i := 0; i < curLen; i++ {
		diffCurEvent[i] = SIEVE_IDX_SKIP
	}
	for i := 0; i < minLen; i++ {
		if subCurEvent, ok := curEvent[i].(map[string]interface{}); ok {
			if subPrevEvent, ok := prevEvent[i].(map[string]interface{}); !ok {
				diffPrevEvent[i] = prevEvent[i]
				diffCurEvent[i] = curEvent[i]
			} else {
				subDiffPrevEvent, subDiffCurEvent := diffEventAsMap(subPrevEvent, subCurEvent)
				if subDiffPrevEvent == nil || subDiffCurEvent == nil {
					continue
				}
				diffPrevEvent[i] = subDiffPrevEvent
				diffCurEvent[i] = subDiffCurEvent
			}
		} else if subCurEvent, ok := curEvent[i].([]interface{}); ok {
			if subPrevEvent, ok := prevEvent[i].([]interface{}); !ok {
				diffPrevEvent[i] = prevEvent[i]
				diffCurEvent[i] = curEvent[i]
			} else {
				subDiffPrevEvent, subDiffCurEvent := diffEventAsList(subPrevEvent, subCurEvent)
				if subDiffPrevEvent == nil || subDiffCurEvent == nil {
					continue
				}
				diffPrevEvent[i] = subDiffPrevEvent
				diffCurEvent[i] = subDiffCurEvent
			}
		} else {
			if !reflect.DeepEqual(prevEvent[i], curEvent[i]) {
				diffPrevEvent[i] = prevEvent[i]
				diffCurEvent[i] = curEvent[i]
			}
		}
	}
	// when the two lists have different length, we simply copy the items with index > minLen
	if prevLen > minLen {
		for i := minLen; i < prevLen; i++ {
			diffPrevEvent[i] = prevEvent[i]
		}
	}
	if curLen > minLen {
		for i := minLen; i < curLen; i++ {
			diffCurEvent[i] = curEvent[i]
		}
	}
	if curLen == prevLen {
		// return nil if the two lists are identical
		keep := false
		for i := 0; i < curLen; i++ {
			if !reflect.DeepEqual(diffPrevEvent[i], SIEVE_IDX_SKIP) || !reflect.DeepEqual(diffCurEvent[i], SIEVE_IDX_SKIP) {
				keep = true
			}
		}
		if !keep {
			return nil, nil
		}
	}
	return diffPrevEvent, diffCurEvent
}

func diffEventAsMap(prevEvent, curEvent map[string]interface{}) (map[string]interface{}, map[string]interface{}) {
	diffPrevEvent := make(map[string]interface{})
	diffCurEvent := make(map[string]interface{})
	for _, key := range mapKeyIntersection(prevEvent, curEvent) {
		if subCurEvent, ok := curEvent[key].(map[string]interface{}); ok {
			if subPrevEvent, ok := prevEvent[key].(map[string]interface{}); !ok {
				diffPrevEvent[key] = prevEvent[key]
				diffCurEvent[key] = curEvent[key]
			} else {
				subDiffPrevEvent, subDiffCurEvent := diffEventAsMap(subPrevEvent, subCurEvent)
				if subDiffPrevEvent == nil || subDiffCurEvent == nil {
					continue
				}
				diffPrevEvent[key] = subDiffPrevEvent
				diffCurEvent[key] = subDiffCurEvent
			}
		} else if subCurEvent, ok := curEvent[key].([]interface{}); ok {
			if subPrevEvent, ok := prevEvent[key].([]interface{}); !ok {
				diffPrevEvent[key] = prevEvent[key]
				diffCurEvent[key] = curEvent[key]
			} else {
				subDiffPrevEvent, subDiffCurEvent := diffEventAsList(subPrevEvent, subCurEvent)
				if subDiffPrevEvent == nil || subDiffCurEvent == nil {
					continue
				}
				diffPrevEvent[key] = subDiffPrevEvent
				diffCurEvent[key] = subDiffCurEvent
			}
		} else {
			if !reflect.DeepEqual(prevEvent[key], curEvent[key]) {
				diffPrevEvent[key] = prevEvent[key]
				diffCurEvent[key] = curEvent[key]
			}
		}
	}
	for _, key := range mapKeyDiff(prevEvent, curEvent) {
		diffPrevEvent[key] = prevEvent[key]
	}
	for _, key := range mapKeyDiff(curEvent, prevEvent) {
		diffCurEvent[key] = curEvent[key]
	}
	if len(diffCurEvent) == 0 && len(diffPrevEvent) == 0 {
		// return nil if the two map are identical
		return nil, nil
	}
	return diffPrevEvent, diffCurEvent
}

func valueShouldBeMasked(value string) bool {
	for _, regex := range MASK_REGS {
		match, err := regexp.MatchString(regex, value)
		if err != nil {
			log.Fatalf("fail to compile %s", TIME_REG)
		}
		if match {
			return true
		}
	}
	return false
}

func canonicalizeValue(value string) string {
	if valueShouldBeMasked(value) {
		return SIEVE_VALUE_MASK
	} else {
		return value
	}
}

func canonicalizeEventAsList(event []interface{}, parentPath string, maskedKeysSet, maskedPathsSet map[string]struct{}) {
	for i, val := range event {
		currentPath := path.Join(parentPath, "*")
		if inSet(currentPath, maskedPathsSet) {
			event[i] = SIEVE_VALUE_MASK
			continue
		}
		switch typedVal := val.(type) {
		case map[string]interface{}:
			canonicalizeEventAsMap(typedVal, currentPath, maskedKeysSet, maskedPathsSet)
		case []interface{}:
			canonicalizeEventAsList(typedVal, currentPath, maskedKeysSet, maskedPathsSet)
		case string:
			event[i] = canonicalizeValue(typedVal)
		}
	}
}

func canonicalizeEventAsMap(event map[string]interface{}, parentPath string, maskedKeysSet, maskedPathsSet map[string]struct{}) {
	for key, val := range event {
		currentPath := path.Join(parentPath, key)
		if inSet(key, maskedKeysSet) || inSet(currentPath, maskedPathsSet) {
			event[key] = SIEVE_VALUE_MASK
			continue
		}
		switch typedVal := val.(type) {
		case map[string]interface{}:
			canonicalizeEventAsMap(typedVal, currentPath, maskedKeysSet, maskedPathsSet)
		case []interface{}:
			canonicalizeEventAsList(typedVal, currentPath, maskedKeysSet, maskedPathsSet)
		case string:
			event[key] = canonicalizeValue(typedVal)
		}
	}
}

func canonicalizeEvent(event map[string]interface{}, maskedKeysSet, maskedPathsSet map[string]struct{}) {
	if _, ok := event[SIEVE_CAN_MARKER]; ok {
		return
	} else {
		canonicalizeEventAsMap(event, "", maskedKeysSet, maskedPathsSet)
		event[SIEVE_CAN_MARKER] = ""
	}
}

func diffEvent(prevEvent, curEvent map[string]interface{}, maskedKeysSet, maskedPathsSet map[string]struct{}) (map[string]interface{}, map[string]interface{}) {
	canonicalizeEvent(prevEvent, maskedKeysSet, maskedPathsSet)
	canonicalizeEvent(curEvent, maskedKeysSet, maskedPathsSet)
	// After canonicalization some values are replaced by SIEVE_VALUE_MASK, we compute diff again
	diffPrevEvent, diffCurEvent := diffEventAsMap(prevEvent, curEvent)
	// Note that we do not perform canonicalization at the beginning as it is more expensive to do so
	return diffPrevEvent, diffCurEvent
}

func equivalentEvent(eventA, eventB map[string]interface{}) bool {
	return reflect.DeepEqual(eventA, eventB)
}

func partOfEventAsList(eventA, eventB []interface{}) bool {
	if len(eventA) != len(eventB) {
		return false
	}
	for i, valA := range eventA {
		if reflect.DeepEqual(valA, SIEVE_IDX_SKIP) {
			continue
		}
		valB := eventB[i]
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
		default:
			if !reflect.DeepEqual(valA, valB) {
				return false
			}
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
		default:
			if !reflect.DeepEqual(valA, valB) {
				return false
			}
		}
	}
	return true
}

func conflictingEvent(eventAType, eventBType string, eventA, eventB map[string]interface{}, maskedKeysSet, maskedPathsSet map[string]struct{}) bool {
	if eventAType == HEAR_DELETED {
		return eventBType != HEAR_DELETED
	} else {
		if eventBType == HEAR_DELETED {
			return true
		} else {
			// assume eventA is already canonicalized
			canonicalizeEvent(eventB, maskedKeysSet, maskedPathsSet)
			return !partOfEventAsMap(eventA, eventB)
		}
	}
}

func isCreationOrDeletion(eventType string) bool {
	isAPICreationOrDeletion := eventType == API_ADDED || eventType == API_DELETED
	isHearCreationOrDeletion := eventType == HEAR_ADDED || eventType == HEAR_DELETED
	isWriteCreationOrDeletion := eventType == WRITE_CREATE || eventType == WRITE_DELETE
	return isAPICreationOrDeletion || isHearCreationOrDeletion || isWriteCreationOrDeletion
}

func findTargetDiff(eventCounter int, onlineCurEventType, targetCurEventType string, onlinePrevEvent, onlineCurEvent, targetDiffPrevEvent, targetDiffCurEvent map[string]interface{}, maskedKeysSet, maskedPathsSet map[string]struct{}, forgiving bool) bool {
	findTargetDiffMutex.Lock()
	defer findTargetDiffMutex.Unlock()
	if seenTargetCounter >= eventCounter {
		return false
	}
	log.Printf("online type: cur: %s\n", onlineCurEventType)
	if onlineCurEventType != targetCurEventType {
		return false
	} else {
		if isCreationOrDeletion(targetCurEventType) {
			seenTargetCounter += 1
			log.Printf("Find the target diff with counter: %d\n", seenTargetCounter)
		} else {
			onlineDiffPrevEvent, onlineDiffCurEvent := diffEvent(onlinePrevEvent, onlineCurEvent, maskedKeysSet, maskedPathsSet)
			log.Printf("online diff: prev: %s\n", mapToStr(onlineDiffPrevEvent))
			log.Printf("online diff: cur: %s\n", mapToStr(onlineDiffCurEvent))
			if equivalentEvent(onlineDiffPrevEvent, targetDiffPrevEvent) && equivalentEvent(onlineDiffCurEvent, targetDiffCurEvent) {
				seenTargetCounter += 1
				log.Printf("Find the target diff with counter: %d\n", seenTargetCounter)
			} else if forgiving {
				if partOfEventAsMap(targetDiffPrevEvent, onlineDiffPrevEvent) && partOfEventAsMap(targetDiffCurEvent, onlineDiffCurEvent) {
					seenTargetCounter += 1
					log.Printf("Find the target diff with counter: %d by being forgiving\n", seenTargetCounter)
				}
			}
		}
	}
	return seenTargetCounter == eventCounter
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

func conformToAPIEvent(event map[string]interface{}) map[string]interface{} {
	// The event object representation is different between the API side and the operator side if it is not CR
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

func conformToAPIPaths(maskedPathsSet map[string]struct{}) map[string]struct{} {
	conformedPathsSet := make(map[string]struct{})
	for key := range maskedPathsSet {
		if strings.HasPrefix(key, "metadata/") {
			conformedPathsSet[strings.TrimPrefix(key, "metadata/")] = exists
		} else {
			tokens := strings.Split(key, "/")
			for i := 0; i < len(tokens); i++ {
				tokens[i] = strings.ToUpper(tokens[i][0:1]) + tokens[i][1:]
			}
			conformedPathsSet[strings.Join(tokens, "/")] = exists
		}
	}
	return conformedPathsSet
}

func conformToAPIKeys(maskedKeysSet map[string]struct{}) map[string]struct{} {
	conformedKeysSet := make(map[string]struct{})
	for key := range maskedKeysSet {
		conformedKeysSet[key] = exists
		conformedKeysSet[strings.ToUpper(key[0:1])+key[1:]] = exists
	}
	return conformedKeysSet
}

// trim kind and apiVersion for atom-vio testing
func trimKindApiversion(event map[string]interface{}) {
	delete(event, "kind")
	delete(event, "apiVersion")
}
