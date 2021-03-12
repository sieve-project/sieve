#!/bin/bash
set -x

make build-go -j10
make build-image
docker tag pravega/zookeeper-operator:latest xudongs/zookeeper-operator:latest
docker push xudongs/zookeeper-operator:latest