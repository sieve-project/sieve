#!/bin/bash
set -x

kubectl create -f crds/yugabyte.com_ybclusters_crd.yaml
kubectl create -f operator.yaml
