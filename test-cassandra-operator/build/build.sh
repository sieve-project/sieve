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

cd docker/cassandra-operator
make
docker tag cassandra-operator:latest ${dockerrepo}/cassandra-operator:${dockertag}
docker push ${dockerrepo}/cassandra-operator:${dockertag}
