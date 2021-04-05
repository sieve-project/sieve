#!/bin/bash

set -ex

kubectl apply -f cr.yaml
sleep 60s
