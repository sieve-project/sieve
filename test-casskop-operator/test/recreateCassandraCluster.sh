#!/bin/bash

set -ex

kubectl apply -f cassandra-configmap-v1.yaml

kubectl apply -f cc-1.yaml
sleep 150s
kubectl delete CassandraCluster sonar-cassandra-cluster
sleep 60s
kubectl apply -f cc-1.yaml
sleep 190s
