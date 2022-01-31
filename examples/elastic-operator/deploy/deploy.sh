#!/bin/bash
set -x

kubectl create -f crds.yaml
kubectl create -f operator.yaml
