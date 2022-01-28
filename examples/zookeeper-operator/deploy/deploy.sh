#!/bin/bash
set -x

kubectl create -f crds
kubectl create -f default_ns/rbac.yaml
kubectl create -f default_ns/operator.yaml
