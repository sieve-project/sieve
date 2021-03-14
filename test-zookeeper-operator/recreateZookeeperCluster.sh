#!/bin/bash

set -ex

kubectl apply -f config/zkc-1.yaml
sleep 30s
kubectl delete ZookeeperCluster sonar-zookeeper-cluster
sleep 25s
kubectl apply -f config/zkc-1.yaml
sleep 50s

