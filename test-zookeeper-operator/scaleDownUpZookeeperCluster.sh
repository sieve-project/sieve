#!/bin/bash

set -ex

kubectl apply -f config/zkc-2.yaml
sleep 60s
kubectl apply -f config/zkc-1.yaml
sleep 40s
kubectl apply -f config/zkc-2.yaml
sleep 15s
