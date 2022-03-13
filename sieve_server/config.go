package main

import (
	"encoding/json"
	"io/ioutil"
	"log"
	"path"
	"regexp"
	"strings"

	"gopkg.in/yaml.v2"
)

func getConfig() map[interface{}]interface{} {

	data, err := ioutil.ReadFile("server.yaml")
	checkError(err)
	m := make(map[interface{}]interface{})

	err = yaml.Unmarshal([]byte(data), &m)
	checkError(err)
	log.Printf("config:\n%v\n", m)

	return m
}

func getMask() (map[string][][]string, map[string][][]string, map[string][][]string) {
	data, err := ioutil.ReadFile("learned_field_path_mask.json")
	checkError(err)
	learnedFieldPathMask := make(map[string][][]string)

	err = json.Unmarshal([]byte(data), &learnedFieldPathMask)
	checkError(err)
	log.Printf("learned mask:\n%v\n", learnedFieldPathMask)

	data, err = ioutil.ReadFile("configured_field_path_mask.json")
	checkError(err)
	configuredFieldPathMask := make(map[string][][]string)

	err = json.Unmarshal([]byte(data), &configuredFieldPathMask)
	checkError(err)
	log.Printf("configured mask:\n%v\n", configuredFieldPathMask)

	data, err = ioutil.ReadFile("configured_field_key_mask.json")
	checkError(err)
	configuredFieldKeyMask := make(map[string][][]string)

	err = json.Unmarshal([]byte(data), &configuredFieldKeyMask)
	checkError(err)
	log.Printf("configured mask:\n%v\n", configuredFieldKeyMask)

	return learnedFieldPathMask, configuredFieldPathMask, configuredFieldKeyMask
}

func wildCardToRegexp(patternWithWildcard string) string {
	var result strings.Builder
	for i, literal := range strings.Split(patternWithWildcard, "*") {

		// Replace * with .*
		if i > 0 {
			result.WriteString(".*")
		}

		// Quote any regular expression meta characters in the
		// literal text.
		result.WriteString(regexp.QuoteMeta(literal))
	}
	return result.String()
}

func getMergedMask() (map[string]map[string]struct{}, map[string]map[string]struct{}) {
	learnedFieldPathMask, configuredFieldPathMask, configuredFieldKeyMask := getMask()
	mergedFieldPathMask := make(map[string]map[string]struct{})
	mergedFieldKeyMask := make(map[string]map[string]struct{})
	for key, val := range learnedFieldPathMask {
		if _, ok := mergedFieldPathMask[key]; !ok {
			mergedFieldPathMask[key] = map[string]struct{}{}
		}
		for _, item := range val {
			maskedPath := strings.Join(item, "/")
			mergedFieldPathMask[key][maskedPath] = exists
		}
	}
	for key, val := range configuredFieldPathMask {
		if _, ok := mergedFieldPathMask[key]; !ok {
			mergedFieldPathMask[key] = map[string]struct{}{}
		}
		for _, item := range val {
			maskedPath := strings.Join(item, "/")
			mergedFieldPathMask[key][maskedPath] = exists
		}
	}
	for key, val := range configuredFieldKeyMask {
		if _, ok := mergedFieldKeyMask[key]; !ok {
			mergedFieldKeyMask[key] = map[string]struct{}{}
		}
		for _, item := range val {
			maskedKey := item[0]
			mergedFieldKeyMask[key][maskedKey] = exists
		}
	}

	handleWildcardsForMask(mergedFieldKeyMask)
	handleWildcardsForMask(mergedFieldPathMask)
	return mergedFieldPathMask, mergedFieldKeyMask
}

func handleWildcardsForMask(mask map[string]map[string]struct{}) {
	// handle keys that contain wildcard
	for resourceKey1 := range mask {
		if strings.Contains(resourceKey1, "*") {
			pattern := resourceKey1
			for resourceKey2 := range mask {
				if !strings.Contains(resourceKey2, "*") {
					matched, err := path.Match(pattern, resourceKey2)
					if err != nil {
						log.Fatalf("error when matching %s with %s: %v", resourceKey2, pattern, err)
					}
					if matched {
						for k := range mask[resourceKey1] {
							mask[resourceKey2][k] = exists
						}
					}
				}
			}
		}
	}
}

func getMaskByResourceKey(mask map[string]map[string]struct{}, resourceKey string) map[string]struct{} {
	if val, ok := mask[resourceKey]; ok {
		return val
	} else {
		mergedMaskLock.Lock()
		defer mergedMaskLock.Unlock()
		if val, ok := mask[resourceKey]; ok {
			return val
		}
		mask[resourceKey] = make(map[string]struct{})
		for existingResourceKey := range mask {
			if strings.Contains(existingResourceKey, "*") {
				pattern := existingResourceKey
				matched, err := path.Match(pattern, resourceKey)
				if err != nil {
					log.Fatalf("error when matching %s with %s: %v", resourceKey, pattern, err)
				}
				if matched {
					for k := range mask[pattern] {
						mask[resourceKey][k] = exists
					}
				}
			}
		}
		return mask[resourceKey]
	}
}
