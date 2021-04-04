#!/bin/bash

set -ex

kubectl apply -f config/cdc-2.yaml
sleep 200s
kubectl apply -f config/cdc-1.yaml
sleep 150s
