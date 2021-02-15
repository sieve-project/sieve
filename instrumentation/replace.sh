#!/bin/bash

cp auto-instr/controller.go /home/xd/go1.13.9/src/github.com/xlab-uiuc/sonar-lib/sigs.k8s.io/controller-runtime@v0.4.0/pkg/internal/controller/controller.go
cp auto-instr/enqueue.go /home/xd/go1.13.9/src/github.com/xlab-uiuc/sonar-lib/sigs.k8s.io/controller-runtime@v0.4.0/pkg/handler/enqueue.go
cp auto-instr/enqueue_mapped.go /home/xd/go1.13.9/src/github.com/xlab-uiuc/sonar-lib/sigs.k8s.io/controller-runtime@v0.4.0/pkg/handler/enqueue_mapped.go
cp auto-instr/enqueue_owner.go /home/xd/go1.13.9/src/github.com/xlab-uiuc/sonar-lib/sigs.k8s.io/controller-runtime@v0.4.0/pkg/handler/enqueue_owner.go
