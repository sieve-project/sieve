#!/bin/bash

set -ex

kubectl apply -f cdc-2.yaml
sleep 170s
kubectl apply -f cdc-1.yaml
sleep 150s
kubectl apply -f cdc-2.yaml
sleep 80s
