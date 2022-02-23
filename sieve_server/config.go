package main

import (
	"encoding/json"
	"io/ioutil"
	"log"
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
	return mergedFieldPathMask, mergedFieldKeyMask
}
