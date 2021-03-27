#!/bin/bash
set -x

dockerrepo=$1
if [ -z "$dockerrepo" ]; then
    dockerrepo="sonar"
fi

cd docker/cassandra-operator
make
docker tag cassandra-operator:latest ${dockerrepo}/cassandra-operator:latest
docker push ${dockerrepo}/cassandra-operator:latest
