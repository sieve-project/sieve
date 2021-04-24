#!/bin/bash

set -ex

kubectl apply -f cdc-2.yaml
if [ $1 = 'learn' ]; then sleep 300s; else sleep 170s; fi
kubectl apply -f cdc-1.yaml
if [ $1 = 'learn' ]; then sleep 300s; else sleep 150s; fi
kubectl apply -f cdc-2.yaml
if [ $1 = 'learn' ]; then sleep 300s; else sleep 80s; fi
