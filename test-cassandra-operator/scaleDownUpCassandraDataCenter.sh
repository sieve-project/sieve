#!/bin/bash

set -ex

kubectl apply -f config/cdc-2.yaml
sleep 170s
echo ">>>" > stdout.txt
kubectl get pods >> stdout.txt
kubectl get pvc >> stdout.txt
kubectl apply -f config/cdc-1.yaml
sleep 150s
echo ">>>" >> stdout.txt
kubectl get pods >> stdout.txt
kubectl get pvc >> stdout.txt
kubectl apply -f config/cdc-2.yaml
sleep 80s
echo ">>>" >> stdout.txt
kubectl get pods >> stdout.txt
kubectl get pvc >> stdout.txt
sleep 80s
echo ">>>" >> stdout.txt
kubectl get pods >> stdout.txt
kubectl get pvc >> stdout.txt
