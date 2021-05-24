#!/bin/bash

set -ex

kubectl apply -f cr-arbiter.yaml
sleep 80s
kubectl patch perconaservermongoDB mongodb-cluster --type='json' -p='[{"op": "replace", "path": "/spec/replsets/0/arbiter/enabled", "value": false}]'
sleep 80s
kubectl patch perconaservermongoDB mongodb-cluster --type='json' -p='[{"op": "replace", "path": "/spec/replsets/0/arbiter/enabled", "value": true}]'
sleep 80s
