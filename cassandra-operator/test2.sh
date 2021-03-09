#!/bin/bash

set -ex

kubectl apply -f cdc-1.yaml
sleep 150s
kubectl delete CassandraDataCenter sonarcassandradatacenter
sleep 50s
kubectl apply -f cdc-1.yaml
sleep 190s

