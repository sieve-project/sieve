package main

import (
	"fmt"
	"os"
	"path"
)

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
	// In reflector.go, we need to create GetExpectedTypeName() in reflector.go
	// because sonar server needs this information.
	reflectorGoFile := path.Join(filepath, "staging", "src", "k8s.io", "client-go", "tools", "cache", "reflector.go")
	fmt.Printf("instrumenting %s\n", reflectorGoFile)
	instrumentReflectorGo(reflectorGoFile, reflectorGoFile)

	// In cacher.go, we need to pass the expectedTypeName from reflector to watch_cache.
	cacherGoFile := path.Join(filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "cacher.go")
	fmt.Printf("instrumenting %s\n", cacherGoFile)
	instrumentCacherGo(cacherGoFile, cacherGoFile)

	// In watch_cache.go, we need to invoke NotifyBeforeProcessEvent in watch_cache.go.
	watchCacheGoFile := path.Join(filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "watch_cache.go")
	fmt.Printf("instrumenting %s\n", watchCacheGoFile)
	instrumentWatchCacheGo(watchCacheGoFile, watchCacheGoFile)
}

func main() {
	args := os.Args
	if args[1] == "sparse-read" {
		instrumentSparseRead(args[2])
	} else if args[1] == "staleness" {
		instrumentTimeTravel(args[2])
	}
}
