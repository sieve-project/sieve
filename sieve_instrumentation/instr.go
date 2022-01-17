package main

import (
	"fmt"
	"os"
	"path"
)

func instrumentKubernetesForTimeTravel(k8s_filepath string) {
	watchCacheGoFile := path.Join(k8s_filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "watch_cache.go")
	fmt.Printf("instrumenting %s\n", watchCacheGoFile)
	preprocess(watchCacheGoFile)
	instrumentWatchCacheGoForAll(watchCacheGoFile, watchCacheGoFile, "TimeTravel", true, true)
}

func instrumentKubernetesForLearn(k8s_filepath string) {
	watchCacheGoFile := path.Join(k8s_filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "watch_cache.go")
	fmt.Printf("instrumenting %s\n", watchCacheGoFile)
	preprocess(watchCacheGoFile)
	instrumentWatchCacheGoForAll(watchCacheGoFile, watchCacheGoFile, "Learn", true, false)
}

func instrumentKubernetesForAtomVio(k8s_filepath string) {
	watchCacheGoFile := path.Join(k8s_filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "watch_cache.go")
	fmt.Printf("instrumenting %s\n", watchCacheGoFile)
	preprocess(watchCacheGoFile)
	instrumentWatchCacheGoForAll(watchCacheGoFile, watchCacheGoFile, "AtomVio", true, false)
}

func instrumentKubernetesForObsGap(k8s_filepath string) {
	watchCacheGoFile := path.Join(k8s_filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "watch_cache.go")
	fmt.Printf("instrumenting %s\n", watchCacheGoFile)
	preprocess(watchCacheGoFile)
	instrumentWatchCacheGoForAll(watchCacheGoFile, watchCacheGoFile, "ObsGap", true, false)
}

func instrumentControllerForObsGap(controller_runtime_filepath string, client_go_filepath string) {
	sharedInformerGoFile := path.Join(client_go_filepath, "tools", "cache", "shared_informer.go")
	fmt.Printf("instrumenting %s\n", sharedInformerGoFile)
	preprocess(sharedInformerGoFile)
	instrumentSharedInformerGoForObsGap(sharedInformerGoFile, sharedInformerGoFile)

	informerCacheGoFile := path.Join(controller_runtime_filepath, "pkg", "cache", "informer_cache.go")
	fmt.Printf("instrumenting %s\n", informerCacheGoFile)
	instrumentInformerCacheGoForObsGap(informerCacheGoFile, informerCacheGoFile)
}

func instrumentControllerForAtomVio(controller_runtime_filepath string, client_go_filepath string) {
	splitGoFile := path.Join(controller_runtime_filepath, "pkg", "client", "split.go")
	fmt.Printf("instrumenting %s\n", splitGoFile)
	instrumentSplitGoForAll(splitGoFile, splitGoFile, "AtomVio")

	clientGoFile := path.Join(controller_runtime_filepath, "pkg", "client", "client.go")
	fmt.Printf("instrumenting %s\n", clientGoFile)
	instrumentClientGoForAll(clientGoFile, clientGoFile, "AtomVio", false)
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
		if mode == TIME_TRAVEL {
			instrumentKubernetesForTimeTravel(args[3])
		} else if mode == LEARN {
			instrumentKubernetesForLearn(args[3])
		} else if mode == ATOM_VIO {
			instrumentKubernetesForAtomVio(args[3])
		} else if mode == OBS_GAP {
			instrumentKubernetesForObsGap(args[3])
		}
	} else {
		if mode == LEARN {
			instrumentControllerForLearn(args[3], args[4])
		} else if mode == OBS_GAP {
			instrumentControllerForObsGap(args[3], args[4])
		} else if mode == ATOM_VIO {
			instrumentControllerForAtomVio(args[3], args[4])
		}

	}
}
