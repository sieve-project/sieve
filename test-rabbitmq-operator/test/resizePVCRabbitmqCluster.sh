#!/bin/bash

set -ex

kubectl apply -f rmqc-1.yaml
sleep 50s
kubectl apply -f rmqc-1-15Gi.yaml
if [ $1 = 'learn' ]; then sleep 100s; else sleep 50s; fi
