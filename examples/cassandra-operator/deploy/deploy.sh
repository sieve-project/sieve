#!/bin/bash
set -x

kubectl apply -f crds.yaml
kubectl apply -f bundle.yaml
