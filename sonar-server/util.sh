#!/bin/bash

project=$1
mode=$2
pod=$3

if [ $project = 'cassandra-operator' ]; then
  if [ $mode = 'crash' ]; then
    kubectl exec $pod -- /bin/bash -c "pkill /cassandra-operator"
  elif [ $mode = 'restart' ]; then
    kubectl exec $pod -- /bin/bash -c "KUBERNETES_SERVICE_HOST=kind-control-plane3 KUBERNETES_SERVICE_PORT=6443 /cassandra-operator &> operator2.log &"
  fi
elif [ $project = 'zookeeper-operator' ]; then
  if [ $mode = 'crash' ]; then
    kubectl exec $pod -- /bin/bash -c "pkill /usr/local/bin/zookeeper-operator"
  elif [ $mode = 'restart' ]; then
    kubectl exec $pod -- /bin/bash -c "KUBERNETES_SERVICE_HOST=kind-control-plane3 KUBERNETES_SERVICE_PORT=6443 /usr/local/bin/zookeeper-operator &> operator2.log &"
  fi
fi
