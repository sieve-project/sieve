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

/usr/bin/env BUILD_IMAGE=laphets/casskop-build REPOSITORY=${dockerrepo}/casskop-operator VERSION=${dockertag} make docker-build
docker push ${dockerrepo}/casskop-operator:${dockertag}
