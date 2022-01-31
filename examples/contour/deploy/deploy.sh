#!/bin/bash
set -x

kubectl apply -f crd.yaml
kubectl apply -f contour.yaml
