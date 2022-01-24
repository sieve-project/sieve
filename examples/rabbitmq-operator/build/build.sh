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


DOCKER_REGISTRY_SERVER=${dockerrepo} OPERATOR_IMAGE=rabbitmq-operator make docker-build
docker tag ${dockerrepo}/rabbitmq-operator:latest ${dockerrepo}/rabbitmq-operator:${dockertag}
