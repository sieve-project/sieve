#!/bin/bash

set -ex

kubectl apply -f config/rmqc-1.yaml
sleep 50s
kubectl delete RabbitmqCluster sonar-rabbitmq-cluster
sleep 50s
kubectl apply -f config/rmqc-1.yaml
sleep 50s
