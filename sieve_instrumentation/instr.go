package main

import (
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"path"

	"gopkg.in/yaml.v2"
)

func instrumentKubernetesForStaleState(k8s_filepath string) {
	watchCacheGoFile := path.Join(k8s_filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "watch_cache.go")
	fmt.Printf("instrumenting %s\n", watchCacheGoFile)
	preprocess(watchCacheGoFile)
	instrumentWatchCacheGoForAll(watchCacheGoFile, watchCacheGoFile, "StaleState", true, true)
}

func instrumentKubernetesForLearn(k8s_filepath string) {
	watchCacheGoFile := path.Join(k8s_filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "watch_cache.go")
	fmt.Printf("instrumenting %s\n", watchCacheGoFile)
	preprocess(watchCacheGoFile)
	instrumentWatchCacheGoForAll(watchCacheGoFile, watchCacheGoFile, "Learn", true, false)
}

func instrumentKubernetesForIntmdState(k8s_filepath string) {
	watchCacheGoFile := path.Join(k8s_filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "watch_cache.go")
	fmt.Printf("instrumenting %s\n", watchCacheGoFile)
	preprocess(watchCacheGoFile)
	instrumentWatchCacheGoForAll(watchCacheGoFile, watchCacheGoFile, "IntmdState", true, false)
}

func instrumentKubernetesForUnobsrState(k8s_filepath string) {
	watchCacheGoFile := path.Join(k8s_filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "watch_cache.go")
	fmt.Printf("instrumenting %s\n", watchCacheGoFile)
	preprocess(watchCacheGoFile)
	instrumentWatchCacheGoForAll(watchCacheGoFile, watchCacheGoFile, "UnobsrState", true, false)
}

func instrumentControllerForUnobsrState(controller_runtime_filepath string, client_go_filepath string) {
	sharedInformerGoFile := path.Join(client_go_filepath, "tools", "cache", "shared_informer.go")
	fmt.Printf("instrumenting %s\n", sharedInformerGoFile)
	preprocess(sharedInformerGoFile)
	instrumentSharedInformerGoForUnobsrState(sharedInformerGoFile, sharedInformerGoFile)

	informerCacheGoFile := path.Join(controller_runtime_filepath, "pkg", "cache", "informer_cache.go")
	fmt.Printf("instrumenting %s\n", informerCacheGoFile)
	instrumentInformerCacheGoForUnobsrState(informerCacheGoFile, informerCacheGoFile)
}

func instrumentControllerForIntmdState(controller_runtime_filepath string, client_go_filepath string) {
	splitGoFile := path.Join(controller_runtime_filepath, "pkg", "client", "split.go")
	fmt.Printf("instrumenting %s\n", splitGoFile)
	instrumentSplitGoForAll(splitGoFile, splitGoFile, "IntmdState")

	clientGoFile := path.Join(controller_runtime_filepath, "pkg", "client", "client.go")
	fmt.Printf("instrumenting %s\n", clientGoFile)
	instrumentClientGoForAll(clientGoFile, clientGoFile, "IntmdState", false)
}

func instrumentControllerForLearn(controller_runtime_filepath, client_go_filepath string) {
	controllerGoFile := path.Join(controller_runtime_filepath, "pkg", "internal", "controller", "controller.go")
	fmt.Printf("instrumenting %s\n", controllerGoFile)
	instrumentControllerGoForLearn(controllerGoFile, controllerGoFile)

	clientGoFile := path.Join(controller_runtime_filepath, "pkg", "client", "client.go")
	fmt.Printf("instrumenting %s\n", clientGoFile)
	instrumentClientGoForAll(clientGoFile, clientGoFile, "Learn", true)

	splitGoFile := path.Join(controller_runtime_filepath, "pkg", "client", "split.go")
	fmt.Printf("instrumenting %s\n", splitGoFile)
	instrumentSplitGoForAll(splitGoFile, splitGoFile, "Learn")

	sharedInformerGoFile := path.Join(client_go_filepath, "tools", "cache", "shared_informer.go")
	fmt.Printf("instrumenting %s\n", sharedInformerGoFile)
	preprocess(sharedInformerGoFile)
	instrumentSharedInformerGoForLearn(sharedInformerGoFile, sharedInformerGoFile)
}

func readConfig(configPath string) map[string]interface{} {
	data, err := ioutil.ReadFile(configPath)
	if err != nil {
		log.Fatalf("Fail due to error: %v\n", err)
	}
	configMap := make(map[string]interface{})
	err = yaml.Unmarshal([]byte(data), &configMap)
	if err != nil {
		log.Fatalf("Fail due to error: %v\n", err)
	}
	return configMap
}

func main() {
	args := os.Args
	configMap := readConfig(args[1])
	project := configMap["project"].(string)
	mode := configMap["mode"].(string)
	if project == "kubernetes" {
		k8s_filepath := configMap["k8s_filepath"].(string)
		if mode == STALE_STATE {
			instrumentKubernetesForStaleState(k8s_filepath)
		} else if mode == LEARN {
			instrumentKubernetesForLearn(k8s_filepath)
		} else if mode == INTERMEDIATE_STATE {
			instrumentKubernetesForIntmdState(k8s_filepath)
		} else if mode == UNOBSERVED_STATE {
			instrumentKubernetesForUnobsrState(k8s_filepath)
		} else if mode == VANILLA {

		} else {
			panic(fmt.Sprintf("Unsupported mode %s", mode))
		}
	} else {
		controller_runtime_filepath := configMap["controller_runtime_filepath"].(string)
		client_go_filepath := configMap["client_go_filepath"].(string)
		if mode == LEARN {
			instrumentControllerForLearn(controller_runtime_filepath, client_go_filepath)
		} else if mode == UNOBSERVED_STATE {
			instrumentControllerForUnobsrState(controller_runtime_filepath, client_go_filepath)
		} else if mode == INTERMEDIATE_STATE {
			instrumentControllerForIntmdState(controller_runtime_filepath, client_go_filepath)
		} else if mode == STALE_STATE {

		} else if mode == VANILLA {

		} else {
			panic(fmt.Sprintf("Unsupported mode %s", mode))
		}

	}
}
