#!/bin/bash

set -ex

kubectl apply -f config/zkc-2.yaml
sleep 60s
echo ">>>" > stdout.txt
kubectl get pods >> stdout.txt
kubectl get pvc >> stdout.txt
kubectl apply -f config/zkc-1.yaml
sleep 40s
echo ">>>" >> stdout.txt
kubectl get pods >> stdout.txt
kubectl get pvc >> stdout.txt
kubectl apply -f config/zkc-2.yaml
sleep 15s
echo ">>>" >> stdout.txt
kubectl get pods >> stdout.txt
kubectl get pvc >> stdout.txt
# sleep 5s
# echo ">>>" >> stdout.txt
# kubectl get pods >> stdout.txt
# kubectl get pvc >> stdout.txt
# sleep 5s
# echo ">>>" >> stdout.txt
# kubectl get pods >> stdout.txt
# kubectl get pvc >> stdout.txt
# sleep 5s
# echo ">>>" >> stdout.txt
# kubectl get pods >> stdout.txt
# kubectl get pvc >> stdout.txt