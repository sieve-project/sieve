#!/bin/bash

set -ex

kubectl apply -f rmqc-1.yaml
sleep 50s
kubectl delete RabbitmqCluster sonar-rabbitmq-cluster
sleep 50s
kubectl apply -f rmqc-1.yaml
if [ $1 = 'learn' ]; then sleep 100s; else sleep 50s; fi
