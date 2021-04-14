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

/usr/bin/env PUSHLATEST=true BUILD_IMAGE=laphets/casskop-build make docker-build
docker tag orangeopensource/casskop:latest ${dockerrepo}/casskop-operator:${dockertag} 
docker push ${dockerrepo}/casskop-operator:${dockertag}
