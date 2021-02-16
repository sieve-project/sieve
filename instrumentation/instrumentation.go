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
	reflectorGoFile1 := path.Join(filepath, "vanilla", "reflector.go")
	reflectorGoFile2 := path.Join(filepath, "auto-instr", "reflector.go")
	fmt.Printf("instrumenting %s\n", reflectorGoFile1)
	instrumentReflectorGo(reflectorGoFile1, reflectorGoFile2)

	cacherGoFile1 := path.Join(filepath, "vanilla", "cacher.go")
	cacherGoFile2 := path.Join(filepath, "auto-instr", "cacher.go")
	fmt.Printf("instrumenting %s\n", cacherGoFile1)
	instrumentCacherGo(cacherGoFile1, cacherGoFile2)
}

func main() {
	args := os.Args
	if args[1] == "sparse-read" {
		instrumentSparseRead(args[2])
	} else if args[1] == "time-travel" {
		instrumentTimeTravel(args[2])
	}
}
