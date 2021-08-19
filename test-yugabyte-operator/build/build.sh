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

export GO111MODULE=on
operator-sdk build ${dockerrepo}/yugabyte-operator:${dockertag}
docker push ${dockerrepo}/yugabyte-operator:${dockertag}