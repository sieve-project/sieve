#!/bin/bash
set -x

make build-go -j10
make build-image
docker tag zookeeper-operator:latest ramanala/zookeeper-operator:latest
docker push ramanala/zookeeper-operator:latest