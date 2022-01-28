#!/bin/bash
set -x

kubectl apply -f role.yaml
./zk.sh
helm install -f values.yaml nifikop-operator .
