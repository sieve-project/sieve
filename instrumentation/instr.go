package main

import (
	"fmt"
	"os"
	"path"
)

// instrment for sparse-read pattern
func instrumentControllerForSparseRead(controller_runtime_filepath string) {
	// Mainly two pieces of instrumentation we should do for sparse-read:
	// In controller.go, we need to invoke NotifySparseReadBeforeReconcile before calling Reconcile(),
	// and invoke NotifySparseReadBeforeMakeQ before creating a queue.
	controllerGoFile := path.Join(controller_runtime_filepath, "pkg", "internal", "controller", "controller.go")
	fmt.Printf("instrumenting %s\n", controllerGoFile)
	instrumentControllerGo(controllerGoFile, controllerGoFile)

	// In enqueue*.go, we need to invoke NotifySparseReadBeforeQAdd before calling each q.Add().
	enqueueGoFile := path.Join(controller_runtime_filepath, "pkg", "handler", "enqueue.go")
	fmt.Printf("instrumenting %s\n", enqueueGoFile)
	instrumentEnqueueGo(enqueueGoFile, enqueueGoFile)

	enqueueMappedGoFile := path.Join(controller_runtime_filepath, "pkg", "handler", "enqueue_mapped.go")
	fmt.Printf("instrumenting %s\n", enqueueMappedGoFile)
	instrumentEnqueueGo(enqueueMappedGoFile, enqueueMappedGoFile)

	enqueueOwnerGoFile := path.Join(controller_runtime_filepath, "pkg", "handler", "enqueue_owner.go")
	fmt.Printf("instrumenting %s\n", enqueueOwnerGoFile)
	instrumentEnqueueGo(enqueueOwnerGoFile, enqueueOwnerGoFile)

	clientGoFile := path.Join(controller_runtime_filepath, "pkg", "client", "client.go")
	fmt.Printf("instrumenting %s\n", clientGoFile)
	instrumentClientGoForAll(clientGoFile, clientGoFile, "SparseRead")
}

func instrumentKubernetesForTimeTravel(k8s_filepath string) {
	// In reflector.go, we need to create GetExpectedTypeName() in reflector.go
	// because sonar server needs this information.
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
	instrumentClientGoForAll(clientGoFile, clientGoFile, "TimeTravel")
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
}

func instrumentControllerForLearn(controller_runtime_filepath, client_go_filepath string) {
	controllerGoFile := path.Join(controller_runtime_filepath, "pkg", "internal", "controller", "controller.go")
	fmt.Printf("instrumenting %s\n", controllerGoFile)
	instrumentControllerGoForLearn(controllerGoFile, controllerGoFile)

	clientGoFile := path.Join(controller_runtime_filepath, "pkg", "client", "client.go")
	fmt.Printf("instrumenting %s\n", clientGoFile)
	instrumentClientGoForAll(clientGoFile, clientGoFile, "Learn")

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
		if mode == "time-travel" {
			instrumentKubernetesForTimeTravel(args[3])
		}
	} else {
		if mode == "time-travel" {
			instrumentControllerForTimeTravel(args[3])
		} else if mode == "sparse-read" {
			instrumentControllerForSparseRead(args[3])
		} else if mode == "learn" {
			instrumentControllerForLearn(args[3], args[4])
		} else if mode == "obs-gap" {
			instrumentControllerForObsGap(args[3], args[4])
		}

	}
}
