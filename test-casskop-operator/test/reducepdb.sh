#!/bin/bash

set -ex

kubectl apply -f cassandra-configmap-v1.yaml

kubectl apply -f cc-2.yaml
sleep 120s
kubectl apply -f cc-1.yaml
sleep 60s
# kubectl apply -f cc-1.yaml
# sleep 120s
