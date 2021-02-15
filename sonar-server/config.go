package main

import (
	"io/ioutil"
	"log"

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

// func sanityCheck(config) {

// }
