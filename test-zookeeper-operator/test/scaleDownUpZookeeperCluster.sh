#!/bin/bash

set -ex

kubectl apply -f zkc-2.yaml
if [ $1 = 'learn' ]; then sleep 400s; else sleep 60s; fi
kubectl patch ZookeeperCluster zookeeper-cluster --type merge -p='{"spec":{"replicas":1}}'
if [ $1 = 'learn' ]; then sleep 300s; else sleep 40s; fi
kubectl patch ZookeeperCluster zookeeper-cluster --type merge -p='{"spec":{"replicas":2}}'
if [ $1 = 'learn' ]; then sleep 150s; else sleep 30s; fi
