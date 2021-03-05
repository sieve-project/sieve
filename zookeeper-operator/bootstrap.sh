#!/bin/bash

kubectl create -f deploy/crds
kubectl create -f deploy/default_ns/rbac.yaml
kubectl create -f deploy/default_ns/operator.yaml
kubectl get deploy
