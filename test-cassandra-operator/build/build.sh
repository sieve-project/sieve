#!/bin/bash
set -x

cd docker/cassandra-operator
make
docker tag cassandra-operator:latest xudongs/cassandra-operator:latest
docker push xudongs/cassandra-operator:latest
