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

sed -i 's/go-generate generate-config-file /go-generate/g'  Makefile

OPERATOR_IMAGE=${dockerrepo}/elastic-operator:${dockertag} make docker-build
