#!/bin/bash

set -ex

echo "====> new round" >> stdout-haproxy.log

kubectl apply -f cr-haproxy-enabled.yaml
sleep 600s
echo "===> apply cr 600s" >> stdout-haproxy.log
kubectl get pods >> stdout-haproxy.log
kubectl get pvc >> stdout-haproxy.log

#kubectl patch perconaxtradbcluster sonar-xtradb-cluster --type merge -p='{"spec":{"haproxy":{"enabled":false}}}'
kubectl apply -f cr-haproxy-disabled.yaml
sleep 450s
echo "===> enable false 450s" >> stdout-haproxy.log
kubectl get pods >> stdout-haproxy.log
kubectl get pvc >> stdout-haproxy.log

#kubectl patch perconaxtradbcluster sonar-xtradb-cluster --type merge -p='{"spec":{"haproxy":{"enabled":true}}}'
kubectl apply -f cr-haproxy-enabled.yaml
sleep 600s
echo "===> enable true 600s" >> stdout-haproxy.log
kubectl get pods >> stdout-haproxy.log
kubectl get pvc >> stdout-haproxy.log