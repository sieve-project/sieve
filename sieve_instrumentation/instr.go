package main

import (
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"path"

	"encoding/json"
)

func instrumentKubernetesForStaleState(k8s_filepath string) {
	watchCacheGoFile := path.Join(k8s_filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "watch_cache.go")
	fmt.Printf("instrumenting %s\n", watchCacheGoFile)
	instrumentWatchCacheGoForAll(watchCacheGoFile, watchCacheGoFile, "StaleState", true, true)
}

func instrumentKubernetesForLearn(k8s_filepath string) {
	watchCacheGoFile := path.Join(k8s_filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "watch_cache.go")
	fmt.Printf("instrumenting %s\n", watchCacheGoFile)
	instrumentWatchCacheGoForAll(watchCacheGoFile, watchCacheGoFile, "Learn", true, false)
}

func instrumentKubernetesForIntmdState(k8s_filepath string) {
	watchCacheGoFile := path.Join(k8s_filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "watch_cache.go")
	fmt.Printf("instrumenting %s\n", watchCacheGoFile)
	instrumentWatchCacheGoForAll(watchCacheGoFile, watchCacheGoFile, "IntmdState", true, false)
}

func instrumentKubernetesForUnobsrState(k8s_filepath string) {
	watchCacheGoFile := path.Join(k8s_filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "watch_cache.go")
	fmt.Printf("instrumenting %s\n", watchCacheGoFile)
	instrumentWatchCacheGoForAll(watchCacheGoFile, watchCacheGoFile, "UnobsrState", true, false)
}

func instrumentControllerForUnobsrState(configMap map[string]interface{}) {
	controller_runtime_filepath := configMap["controller_runtime_filepath"].(string)
	client_go_filepath := configMap["client_go_filepath"].(string)

	sharedInformerGoFile := path.Join(client_go_filepath, "tools", "cache", "shared_informer.go")
	fmt.Printf("instrumenting %s\n", sharedInformerGoFile)
	instrumentSharedInformerGoForUnobsrState(sharedInformerGoFile, sharedInformerGoFile)

	informerCacheGoFile := path.Join(controller_runtime_filepath, "pkg", "cache", "informer_cache.go")
	fmt.Printf("instrumenting %s\n", informerCacheGoFile)
	instrumentInformerCacheGoForUnobsrState(informerCacheGoFile, informerCacheGoFile)
}

func instrumentControllerForIntmdState(configMap map[string]interface{}) {
	controller_runtime_filepath := configMap["controller_runtime_filepath"].(string)

	splitGoFile := path.Join(controller_runtime_filepath, "pkg", "client", "split.go")
	fmt.Printf("instrumenting %s\n", splitGoFile)
	instrumentSplitGoForAll(splitGoFile, splitGoFile, "IntmdState")

	clientGoFile := path.Join(controller_runtime_filepath, "pkg", "client", "client.go")
	fmt.Printf("instrumenting %s\n", clientGoFile)
	instrumentClientGoForAll(clientGoFile, clientGoFile, "IntmdState", false)
}

func instrumentControllerForLearn(configMap map[string]interface{}) {
	application_file_path := configMap["app_file_path"].(string)
	controller_runtime_filepath := configMap["controller_runtime_filepath"].(string)
	client_go_filepath := configMap["client_go_filepath"].(string)
	apis_to_instrument := configMap["apis_to_instrument"].([]interface{})

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
	instrumentSharedInformerGoForLearn(sharedInformerGoFile, sharedInformerGoFile)

	for _, api_to_instrument := range apis_to_instrument {
		entry := api_to_instrument.(map[string]interface{})
		module := entry["module"].(string)
		file_path := entry["file_path"].(string)
		pkg := entry["package"].(string)
		funName := entry["func_name"].(string)
		typeName := entry["type_name"].(string)
		customizedImportMap := map[string]string{}
		if val, ok := entry["import_map"]; ok {
			tempMap := val.(map[string]interface{})
			for key, val := range tempMap {
				customizedImportMap[key] = val.(string)
			}
		}
		source_file_to_instrument := path.Join(application_file_path, "sieve-dependency", "src", module, file_path)
		instrumentNonK8sAPI(source_file_to_instrument, source_file_to_instrument, pkg, funName, typeName, "Learn", customizedImportMap)
	}
}

func readConfig(configPath string) map[string]interface{} {
	data, err := ioutil.ReadFile(configPath)
	if err != nil {
		log.Fatalf("Fail due to error: %v\n", err)
	}
	configMap := make(map[string]interface{})
	err = json.Unmarshal([]byte(data), &configMap)
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
		if mode == LEARN {
			instrumentControllerForLearn(configMap)
		} else if mode == UNOBSERVED_STATE {
			instrumentControllerForUnobsrState(configMap)
		} else if mode == INTERMEDIATE_STATE {
			instrumentControllerForIntmdState(configMap)
		} else if mode == STALE_STATE {

		} else if mode == VANILLA {

		} else {
			panic(fmt.Sprintf("Unsupported mode %s", mode))
		}

	}
}
