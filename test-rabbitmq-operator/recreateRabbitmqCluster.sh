#!/bin/bash

set -ex

kubectl apply -f config/rmqc-1.yaml
if [ $1 = 'learn' ]; then sleep 200s; else sleep 50s; fi
echo ">>>" > stdout.txt
kubectl get pods >> stdout.txt
kubectl get sts >> stdout.txt
kubectl get pvc >> stdout.txt
kubectl delete RabbitmqCluster sonar-rabbitmq-cluster
if [ $1 = 'learn' ]; then sleep 200s; else sleep 50s; fi
echo ">>>" >> stdout.txt
kubectl get pods >> stdout.txt
kubectl get sts >> stdout.txt
kubectl get pvc >> stdout.txt
kubectl apply -f config/rmqc-1.yaml
if [ $1 = 'learn' ]; then sleep 200s; else sleep 50s; fi
echo ">>>" >> stdout.txt
kubectl get pods >> stdout.txt
kubectl get sts >> stdout.txt
kubectl get pvc >> stdout.txt
