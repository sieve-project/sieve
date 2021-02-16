package main

import (
	"fmt"
	"os"
	"path"
)

func instrumentSparseRead(filepath string) {
	controllerGoFile := path.Join(filepath, "pkg", "internal", "controller", "controller.go")
	fmt.Printf("instrumenting %s\n", controllerGoFile)
	instrumentControllerGo(controllerGoFile, controllerGoFile)

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

func instrumentTimeTravel(filepath string) {
	reflectorGoFile := path.Join(filepath, "staging", "src", "k8s.io", "client-go", "tools", "cache", "reflector.go")
	fmt.Printf("instrumenting %s\n", reflectorGoFile)
	instrumentReflectorGo(reflectorGoFile, reflectorGoFile)

	cacherGoFile := path.Join(filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "cacher.go")
	fmt.Printf("instrumenting %s\n", cacherGoFile)
	instrumentCacherGo(cacherGoFile, cacherGoFile)

	watchCacheGoFile := path.Join(filepath, "staging", "src", "k8s.io", "apiserver", "pkg", "storage", "cacher", "watch_cache.go")
	fmt.Printf("instrumenting %s\n", watchCacheGoFile)
	instrumentWatchCacheGo(watchCacheGoFile, watchCacheGoFile)
}

func main() {
	args := os.Args
	if args[1] == "sparse-read" {
		instrumentSparseRead(args[2])
	} else if args[1] == "time-travel" {
		instrumentTimeTravel(args[2])
	}
}
