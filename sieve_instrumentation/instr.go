package main

import (
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"path"

	"encoding/json"
)

func instrumentKubernetesForTest(k8s_filepath string) {
	watchCacheGoFile := path.Join(k8s_filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "watch_cache.go")
	fmt.Printf("instrumenting %s\n", watchCacheGoFile)
	instrumentWatchCacheGoForAll(watchCacheGoFile, watchCacheGoFile, "Test", true, true)
}

func instrumentKubernetesForLearn(k8s_filepath string) {
	watchCacheGoFile := path.Join(k8s_filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "watch_cache.go")
	fmt.Printf("instrumenting %s\n", watchCacheGoFile)
	instrumentWatchCacheGoForAll(watchCacheGoFile, watchCacheGoFile, "Learn", true, false)
}

func instrumentControllerForLearn(configMap map[string]interface{}) {
	application_file_path := configMap["app_file_path"].(string)
	controller_runtime_filepath := configMap["controller_runtime_filepath"].(string)
	client_go_filepath := configMap["client_go_filepath"].(string)
	apis_to_instrument := configMap["apis_to_instrument"].([]interface{})

	sharedInformerGoFile := path.Join(client_go_filepath, "tools", "cache", "shared_informer.go")
	fmt.Printf("instrumenting %s\n", sharedInformerGoFile)
	instrumentSharedInformerGoForAll(sharedInformerGoFile, sharedInformerGoFile, "Learn")

	requestGoFile := path.Join(client_go_filepath, "rest", "request.go")
	fmt.Printf("instrumenting %s\n", requestGoFile)
	instrumentRequestGoForAll(requestGoFile, requestGoFile, "Learn")

	storeGoFile := path.Join(client_go_filepath, "tools", "cache", "store.go")
	fmt.Printf("instrumenting %s\n", storeGoFile)
	instrumentStoreGoForAll(storeGoFile, storeGoFile, "Learn")

	controllerGoFile := path.Join(controller_runtime_filepath, "pkg", "internal", "controller", "controller.go")
	fmt.Printf("instrumenting %s\n", controllerGoFile)
	instrumentControllerGoForLearn(controllerGoFile, controllerGoFile)

	// splitGoFile := path.Join(controller_runtime_filepath, "pkg", "client", "split.go")
	// fmt.Printf("instrumenting %s\n", splitGoFile)
	// instrumentSplitGoForAll(splitGoFile, splitGoFile, "Learn")

	for _, api_to_instrument := range apis_to_instrument {
		entry := api_to_instrument.(map[string]interface{})
		module := entry["module"].(string)
		filePath := entry["file_path"].(string)
		pkg := entry["package"].(string)
		funName := entry["func_name"].(string)
		recvType := entry["receiver_type"].(string)
		customizedImportMap := map[string]string{}
		if val, ok := entry["import_map"]; ok {
			tempMap := val.(map[string]interface{})
			for key, val := range tempMap {
				customizedImportMap[key] = val.(string)
			}
		}
		source_file_to_instrument := path.Join(application_file_path, "sieve-dependency", "src", module, filePath)
		instrumentAnnotatedAPI(source_file_to_instrument, source_file_to_instrument, module, filePath, pkg, funName, recvType, "Learn", customizedImportMap, true)
	}
}

func instrumentControllerForTest(configMap map[string]interface{}) {
	// controller_runtime_filepath := configMap["controller_runtime_filepath"].(string)
	client_go_filepath := configMap["client_go_filepath"].(string)
	application_file_path := configMap["app_file_path"].(string)
	apis_to_instrument := configMap["apis_to_instrument"].([]interface{})

	requestGoFile := path.Join(client_go_filepath, "rest", "request.go")
	fmt.Printf("instrumenting %s\n", requestGoFile)
	instrumentRequestGoForAll(requestGoFile, requestGoFile, "Test")

	sharedInformerGoFile := path.Join(client_go_filepath, "tools", "cache", "shared_informer.go")
	fmt.Printf("instrumenting %s\n", sharedInformerGoFile)
	instrumentSharedInformerGoForAll(sharedInformerGoFile, sharedInformerGoFile, "Test")

	storeGoFile := path.Join(client_go_filepath, "tools", "cache", "store.go")
	fmt.Printf("instrumenting %s\n", storeGoFile)
	instrumentStoreGoForAll(storeGoFile, storeGoFile, "Test")

	for _, api_to_instrument := range apis_to_instrument {
		entry := api_to_instrument.(map[string]interface{})
		module := entry["module"].(string)
		filePath := entry["file_path"].(string)
		pkg := entry["package"].(string)
		funName := entry["func_name"].(string)
		recvType := entry["receiver_type"].(string)
		customizedImportMap := map[string]string{}
		if val, ok := entry["import_map"]; ok {
			tempMap := val.(map[string]interface{})
			for key, val := range tempMap {
				customizedImportMap[key] = val.(string)
			}
		}
		source_file_to_instrument := path.Join(application_file_path, "sieve-dependency", "src", module, filePath)
		instrumentAnnotatedAPI(source_file_to_instrument, source_file_to_instrument, module, filePath, pkg, funName, recvType, "Test", customizedImportMap, true)
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
		if mode == LEARN {
			instrumentKubernetesForLearn(k8s_filepath)
		} else if mode == TEST {
			instrumentKubernetesForTest(k8s_filepath)
		} else if mode == VANILLA {

		} else {
			panic(fmt.Sprintf("Unsupported mode %s", mode))
		}
	} else {
		if mode == LEARN {
			instrumentControllerForLearn(configMap)
		} else if mode == TEST {
			instrumentControllerForTest(configMap)
		} else if mode == VANILLA {

		} else {
			panic(fmt.Sprintf("Unsupported mode %s", mode))
		}
	}
}
