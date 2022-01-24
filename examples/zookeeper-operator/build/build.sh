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


make build-image
docker tag pravega/zookeeper-operator:latest ${dockerrepo}/zookeeper-operator:${dockertag}
