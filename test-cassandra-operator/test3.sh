#!/bin/bash

set -ex

kubectl apply -f cdc-1.yaml
sleep 150s
kubectl delete CassandraDataCenter sonarcassandradatacenter
sleep 60s
kubectl apply -f cdc-1-2.yaml
sleep 150s

