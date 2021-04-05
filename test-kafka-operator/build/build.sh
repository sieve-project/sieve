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

make docker-build IMG=${dockerrepo}/kafka-operator:${dockertag}
make docker-push IMG=${dockerrepo}/kafka-operator:${dockertag}
