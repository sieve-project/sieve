#!/bin/bash
set -x

kubectl apply -f release.yml
kubectl apply -f default-ns.yml
