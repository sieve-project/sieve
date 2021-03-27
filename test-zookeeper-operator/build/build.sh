#!/bin/bash
set -x

dockerrepo=$1
if [ -z "$dockerrepo" ]; then
    dockerrepo="sonar"
fi

make build-go -j10
make build-image
docker tag pravega/zookeeper-operator:latest ${dockerrepo}/zookeeper-operator:latest
docker push ${dockerrepo}/zookeeper-operator:latest
