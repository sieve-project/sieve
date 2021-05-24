#!/bin/bash

set -ex

kubectl apply -f cdc-2.yaml
if [ $1 = 'learn' ]; then sleep 300s; else sleep 170s; fi
kubectl patch CassandraDataCenter cassandra-datacenter --type merge -p='{"spec":{"nodes":1}}'
if [ $1 = 'learn' ]; then sleep 300s; else sleep 150s; fi
kubectl patch CassandraDataCenter cassandra-datacenter --type merge -p='{"spec":{"nodes":2}}'
if [ $1 = 'learn' ]; then sleep 300s; else sleep 80s; fi
