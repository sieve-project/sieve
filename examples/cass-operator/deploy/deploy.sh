#!/bin/bash
set -x

kubectl apply -f controller-manifest.yaml
kubectl apply -f storageClass.yaml
