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

mage operator:clean
mage operator:buildDocker
docker tag datastax/cass-operator:latest ${dockerrepo}/cass-operator:${dockertag}
docker push ${dockerrepo}/cass-operator:${dockertag}
