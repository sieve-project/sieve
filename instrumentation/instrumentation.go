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

func main() {
	args := os.Args
	if args[1] == "sparse-read" {
		instrumentSparseRead(args[2])
	}
}
