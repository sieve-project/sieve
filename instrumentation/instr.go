package main

import (
	"fmt"
	"os"
	"path"
)

func instrumentKubernetesForTimeTravel(k8s_filepath string) {
	// In reflector.go, we need to create GetExpectedTypeName() in reflector.go
	// because sieve server needs this information.
	// reflectorGoFile := path.Join(filepath, "staging", "src", "k8s.io", "client-go", "tools", "cache", "reflector.go")
	// fmt.Printf("instrumenting %s\n", reflectorGoFile)
	// instrumentReflectorGo(reflectorGoFile, reflectorGoFile)

	// In cacher.go, we need to pass the expectedTypeName from reflector to watch_cache.
	// cacherGoFile := path.Join(filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "cacher.go")
	// fmt.Printf("instrumenting %s\n", cacherGoFile)
	// instrumentCacherGo(cacherGoFile, cacherGoFile)

	watchCacheGoFile := path.Join(k8s_filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "watch_cache.go")
	fmt.Printf("instrumenting %s\n", watchCacheGoFile)
	instrumentWatchCacheGoForTimeTravel(watchCacheGoFile, watchCacheGoFile)
}

func instrumentControllerForTimeTravel(controller_runtime_filepath string) {
	clientGoFile := path.Join(controller_runtime_filepath, "pkg", "client", "client.go")
	fmt.Printf("instrumenting %s\n", clientGoFile)
	instrumentClientGoForAllTest(clientGoFile, clientGoFile, "TimeTravel")
}

/* API interface:
1. notify that we get some event into localcache (just recv event from API server) (cannot be runtime, but it is bind with watch(?))
2. block the reconcile (in runtime)
*/
func instrumentControllerForObsGap(controller_runtime_filepath string, client_go_filepath string) {
	// client.go: before apply to cache
	controllerGoFile := path.Join(controller_runtime_filepath, "pkg", "internal", "controller", "controller.go")
	fmt.Printf("instrumenting %s\n", controllerGoFile)
	instrumentControllerGoForObsGap(controllerGoFile, controllerGoFile)

	sharedInformerGoFile := path.Join(client_go_filepath, "tools", "cache", "shared_informer.go")
	fmt.Printf("instrumenting %s\n", sharedInformerGoFile)
	preprocess(sharedInformerGoFile)
	instrumentSharedInformerGoForObsGap(sharedInformerGoFile, sharedInformerGoFile)

	clientGoFile := path.Join(controller_runtime_filepath, "pkg", "client", "client.go")
	fmt.Printf("instrumenting %s\n", clientGoFile)
	instrumentClientGoForAllTest(clientGoFile, clientGoFile, "ObsGap")
}

func instrumentControllerForAtomVio(controller_runtime_filepath string, client_go_filepath string) {
	sharedInformerGoFile := path.Join(client_go_filepath, "tools", "cache", "shared_informer.go")
	fmt.Printf("instrumenting %s\n", sharedInformerGoFile)
	preprocess(sharedInformerGoFile)
	instrumentSharedInformerGoForAtomVio(sharedInformerGoFile, sharedInformerGoFile)

	clientGoFile := path.Join(controller_runtime_filepath, "pkg", "client", "client.go")
	fmt.Printf("instrumenting %s\n", clientGoFile)
	instrumentClientGoForAtomVio(clientGoFile, clientGoFile)
	instrumentClientGoForAllTest(clientGoFile, clientGoFile, "AtomVio")
}

func instrumentControllerForLearn(controller_runtime_filepath, client_go_filepath string) {
	controllerGoFile := path.Join(controller_runtime_filepath, "pkg", "internal", "controller", "controller.go")
	fmt.Printf("instrumenting %s\n", controllerGoFile)
	instrumentControllerGoForLearn(controllerGoFile, controllerGoFile)

	clientGoFile := path.Join(controller_runtime_filepath, "pkg", "client", "client.go")
	fmt.Printf("instrumenting %s\n", clientGoFile)
	instrumentClientGoForLearn(clientGoFile, clientGoFile)

	splitGoFile := path.Join(controller_runtime_filepath, "pkg", "client", "split.go")
	fmt.Printf("instrumenting %s\n", splitGoFile)
	instrumentSplitGoForLearn(splitGoFile, splitGoFile)

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
		}
	} else {
		if mode == TIME_TRAVEL {
			instrumentControllerForTimeTravel(args[3])
		} else if mode == LEARN {
			instrumentControllerForLearn(args[3], args[4])
		} else if mode == OBS_GAP {
			instrumentControllerForObsGap(args[3], args[4])
		} else if mode == ATOM_VIO {
			instrumentControllerForAtomVio(args[3], args[4])
		}

	}
}
