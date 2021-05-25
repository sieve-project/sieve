#!/bin/bash

set -ex

echo "====> new round" >> stdout.txt
kubectl apply -f cr.yaml
sleep 420s
echo "====> apply" >> stdout.txt
kubectl get pods >> stdout.txt
kubectl get pvc >> stdout.txt

kubectl delete perconaxtradbcluster sonar-xtradb-cluster
sleep 240s
echo "====> delete" >> stdout.txt
kubectl get pods >> stdout.txt
kubectl get pvc >> stdout.txt

kubectl apply -f cr.yaml
sleep 420s
echo "====> reapply" >> stdout.txt
kubectl get pods >> stdout.txt
kubectl get pvc >> stdout.txt
