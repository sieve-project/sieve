#!/bin/bash
set -x

dockerrepo=$1
if [ -z "$dockerrepo" ]; then
    dockerrepo="xudongs"
fi


DOCKER_REGISTRY_SERVER=${dockerrepo} OPERATOR_IMAGE=rabbitmq-operator make docker-build
docker push ${dockerrepo}/rabbitmq-operator:latest
