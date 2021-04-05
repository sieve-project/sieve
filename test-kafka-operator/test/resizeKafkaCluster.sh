#!/bin/bash

set -ex

kubectl apply -f kfkc-3.yaml
sleep 300
kubectl apply -f kfkc-2.yaml
sleep 90
