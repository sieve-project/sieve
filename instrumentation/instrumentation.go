package main

import (
	"fmt"
	"os"
	"path"
)

func instrumentForAll(filepath string) {
	// In reflector.go, we need to create GetExpectedTypeName() in reflector.go
	// because sonar server needs this information.
	reflectorGoFile := path.Join(filepath, "staging", "src", "k8s.io", "client-go", "tools", "cache", "reflector.go")
	fmt.Printf("instrumenting %s\n", reflectorGoFile)
	instrumentReflectorGo(reflectorGoFile, reflectorGoFile)

	// In cacher.go, we need to pass the expectedTypeName from reflector to watch_cache.
	cacherGoFile := path.Join(filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "cacher.go")
	fmt.Printf("instrumenting %s\n", cacherGoFile)
	instrumentCacherGo(cacherGoFile, cacherGoFile)
}

// instrment for sparse-read pattern
func instrumentSparseRead(filepath string) {
	// Mainly two pieces of instrumentation we should do for sparse-read:
	// In controller.go, we need to invoke NotifyBeforeReconcile before calling Reconcile(),
	// and invoke NotifyBeforeMakeQ before creating a queue.
	controllerGoFile := path.Join(filepath, "pkg", "internal", "controller", "controller.go")
	fmt.Printf("instrumenting %s\n", controllerGoFile)
	instrumentControllerGo(controllerGoFile, controllerGoFile)

	// In enqueue*.go, we need to invoke NotifyBeforeQAdd before calling each q.Add().
	enqueueGoFile := path.Join(filepath, "pkg", "handler", "enqueue.go")
	fmt.Printf("instrumenting %s\n", enqueueGoFile)
	instrumentEnqueueGo(enqueueGoFile, enqueueGoFile)

	enqueueMappedGoFile := path.Join(filepath, "pkg", "handler", "enqueue_mapped.go")
	fmt.Printf("instrumenting %s\n", enqueueMappedGoFile)
	instrumentEnqueueGo(enqueueMappedGoFile, enqueueMappedGoFile)

	enqueueOwnerGoFile := path.Join(filepath, "pkg", "handler", "enqueue_owner.go")
	fmt.Printf("instrumenting %s\n", enqueueOwnerGoFile)
	instrumentEnqueueGo(enqueueOwnerGoFile, enqueueOwnerGoFile)
}

// instrument for time-traveling pattern
func instrumentTimeTravel(filepath string) {
	// In watch_cache.go, we need to invoke NotifyBeforeProcessEvent in watch_cache.go.
	watchCacheGoFile := path.Join(filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "watch_cache.go")
	fmt.Printf("instrumenting %s\n", watchCacheGoFile)
	instrumentWatchCacheGo(watchCacheGoFile, watchCacheGoFile)
}

func instrumentLearn(controller_runtime_filepath, client_go_filepath string) {
	controllerGoFile := path.Join(controller_runtime_filepath, "pkg", "internal", "controller", "controller.go")
	fmt.Printf("instrumenting %s\n", controllerGoFile)
	instrumentControllerGoForLearn(controllerGoFile, controllerGoFile)

	clientGoFile := path.Join(controller_runtime_filepath, "pkg", "client", "client.go")
	fmt.Printf("instrumenting %s\n", clientGoFile)
	instrumentClientGoForLearn(clientGoFile, clientGoFile)

	// enqueueGoFile := path.Join(controller_runtime_filepath, "pkg", "handler", "enqueue.go")
	// fmt.Printf("instrumenting %s\n", enqueueGoFile)
	// instrumentEnqueueGoForLearn(enqueueGoFile, enqueueGoFile)

	// enqueueMappedGoFile := path.Join(controller_runtime_filepath, "pkg", "handler", "enqueue_mapped.go")
	// fmt.Printf("instrumenting %s\n", enqueueMappedGoFile)
	// instrumentEnqueueGoForLearn(enqueueMappedGoFile, enqueueMappedGoFile)

	// enqueueOwnerGoFile := path.Join(controller_runtime_filepath, "pkg", "handler", "enqueue_owner.go")
	// fmt.Printf("instrumenting %s\n", enqueueOwnerGoFile)
	// instrumentEnqueueGoForLearn(enqueueOwnerGoFile, enqueueOwnerGoFile)

	reflectorGoFile := path.Join(client_go_filepath, "tools", "cache", "shared_informer.go")
	fmt.Printf("instrumenting %s\n", reflectorGoFile)
	instrumentSharedInformerGoForLearn(reflectorGoFile, reflectorGoFile)
}

func main() {
	args := os.Args
	if args[1] == "sparse-read" {
		instrumentForAll(args[2])
		instrumentSparseRead(args[3])
	} else if args[1] == "time-travel" {
		instrumentForAll(args[2])
		instrumentTimeTravel(args[2])
	} else if args[1] == "learn" {
		instrumentLearn(args[2], args[3])
	}
}
