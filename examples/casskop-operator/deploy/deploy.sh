#!/bin/bash
set -x

helm install -f values.yaml casskop-operator .
