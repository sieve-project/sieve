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

docker build \
    --no-cache \
    -t "${dockerrepo}/yugabyte-operator:${dockertag}" -f build/Dockerfile .
docker push ${dockerrepo}/yugabyte-operator:${dockertag}