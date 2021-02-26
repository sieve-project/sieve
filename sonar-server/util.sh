#!/bin/bash

mode=$1
pod=$2

if [[ "$mode" == "crash" ]]; then
  kubectl exec $pod -- /bin/bash -c "pkill ./cassandra-operator"
elif [[ "$mode" == "restart" ]]; then
  kubectl exec $pod -- /bin/bash -c "KUBERNETES_SERVICE_HOST=kind-control-plane2 KUBERNETES_SERVICE_PORT=6443 ./cassandra-operator &> operator2.log &"
fi
