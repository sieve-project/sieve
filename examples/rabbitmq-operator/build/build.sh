#!/bin/bash
set -x

DOCKER_REGISTRY_SERVER=rabbitmq OPERATOR_IMAGE=rabbitmq-operator make docker-build
