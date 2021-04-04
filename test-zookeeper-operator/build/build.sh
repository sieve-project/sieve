#!/bin/bash
set -x

dockerrepo=$1
dockertag=$2
if [ -z "$dockerrepo" ]; then
    exit 1
fi
if [ -z "$dockertag" ]; then
    exit 1
fi

make build-go -j10
make build-image
docker tag pravega/zookeeper-operator:latest ${dockerrepo}/zookeeper-operator:${dockertag}
docker push ${dockerrepo}/zookeeper-operator:${dockertag}
