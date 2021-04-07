#!/bin/bash

set -ex

kubectl apply -f cdc-1.yaml
sleep 180s
echo '====' >> stdout.txt
kubectl get pods >> stdout.txt
kubectl get pvc >> stdout.txt

kubectl delete CassandraDatacenter sonar-cassandra-datacenter
sleep 180s
echo '====' >> stdout.txt
kubectl get pods >> stdout.txt
kubectl get pvc >> stdout.txt

kubectl apply -f cdc-1.yaml
sleep 180s
echo '====' >> stdout.txt
kubectl get pods >> stdout.txt
kubectl get pvc >> stdout.txt