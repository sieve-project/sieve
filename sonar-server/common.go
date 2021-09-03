package main

import (
	"io/ioutil"
	"log"

	"gopkg.in/yaml.v2"
)

const TIME_TRAVEL string = "time-travel"
const OBS_GAP string = "observability-gap"
const ATOM_VIO string = "atomicity-violation"
const TEST string = "test"
const LEARN string = "learn"

func getConfig() map[interface{}]interface{} {

	data, err := ioutil.ReadFile("server.yaml")
	checkError(err)
	m := make(map[interface{}]interface{})

	err = yaml.Unmarshal([]byte(data), &m)
	checkError(err)
	log.Printf("config:\n%v\n", m)

	return m
}
