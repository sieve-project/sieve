#!/bin/bash

set -ex

echo "====> new round" >> stdout.txt
kubectl apply -f cr.yaml
sleep 490s
echo "====> apply" >> stdout.txt
kubectl get pods >> stdout.txt
kubectl get pvc >> stdout.txt

kubectl delete perconaservermongodb sonar-mongodb-cluster
sleep 240s
echo "====> delete" >> stdout.txt
kubectl get pods >> stdout.txt
kubectl get pvc >> stdout.txt

kubectl apply -f cr.yaml
sleep 490s
echo "====> reapply" >> stdout.txt
kubectl get pods >> stdout.txt
kubectl get pvc >> stdout.txt
