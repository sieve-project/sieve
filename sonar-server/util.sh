#!/bin/bash

command=$1
pod=$2
straggler=$3

kubectl exec $pod -- /bin/bash -c "pkill $command"
kubectl exec $pod -- /bin/bash -c "echo after restart... >> operator.log"
kubectl exec $pod -- /bin/bash -c "KUBERNETES_SERVICE_HOST=$straggler KUBERNETES_SERVICE_PORT=6443 $command >> operator.log 2>&1 &"

# if [ $project = 'cassandra-operator' ]; then
#   if [ $mode = 'crash' ]; then
#     kubectl exec $pod -- /bin/bash -c "pkill /cassandra-operator"
#   elif [ $mode = 'restart' ]; then
#     kubectl exec $pod -- /bin/bash -c "echo after restart... >> operator.log"
#     kubectl exec $pod -- /bin/bash -c "KUBERNETES_SERVICE_HOST=kind-control-plane3 KUBERNETES_SERVICE_PORT=6443 /cassandra-operator >> operator.log 2>&1 &"
#   fi
# elif [ $project = 'zookeeper-operator' ]; then
#   if [ $mode = 'crash' ]; then
#     kubectl exec $pod -- /bin/bash -c "pkill /usr/local/bin/zookeeper-operator"
#   elif [ $mode = 'restart' ]; then
#     kubectl exec $pod -- /bin/bash -c "echo after restart... >> operator.log"
#     kubectl exec $pod -- /bin/bash -c "KUBERNETES_SERVICE_HOST=kind-control-plane3 KUBERNETES_SERVICE_PORT=6443 /usr/local/bin/zookeeper-operator >> operator.log 2>&1 &"
#   fi
# fi
