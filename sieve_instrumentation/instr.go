package main

import (
	"fmt"
	"os"
	"path"
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

func main() {
	args := os.Args
	project := args[1]
	mode := args[2]
	if project == "kubernetes" {
		if mode == STALE_STATE {
			instrumentKubernetesForStaleState(args[3])
		} else if mode == LEARN {
			instrumentKubernetesForLearn(args[3])
		} else if mode == INTERMEDIATE_STATE {
			instrumentKubernetesForIntmdState(args[3])
		} else if mode == UNOBSERVED_STATE {
			instrumentKubernetesForUnobsrState(args[3])
		} else if mode == VANILLA {

		} else {
			panic(fmt.Sprintf("Unsupported mode %s", mode))
		}
	} else {
		if mode == LEARN {
			instrumentControllerForLearn(args[3], args[4])
		} else if mode == UNOBSERVED_STATE {
			instrumentControllerForUnobsrState(args[3], args[4])
		} else if mode == INTERMEDIATE_STATE {
			instrumentControllerForIntmdState(args[3], args[4])
		} else if mode == STALE_STATE {

		} else if mode == VANILLA {

		} else {
			panic(fmt.Sprintf("Unsupported mode %s", mode))
		}

	}
}
