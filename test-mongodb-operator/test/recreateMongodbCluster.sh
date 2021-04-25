#!/bin/bash

set -ex

kubectl apply -f cr.yaml
sleep 70s
kubectl delete perconaservermongodb mongodb-cluster
sleep 60s
kubectl apply -f cr.yaml
sleep 80s
