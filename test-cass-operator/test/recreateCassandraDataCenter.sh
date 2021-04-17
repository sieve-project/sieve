#!/bin/bash

set -ex

kubectl apply -f cdc-1.yaml
sleep 180s

kubectl delete CassandraDatacenter sonar-cassandra-datacenter
sleep 180s

kubectl apply -f cdc-1.yaml
sleep 180s
