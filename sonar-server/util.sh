#!/bin/bash

command=$1
pod=$2
straggler=$3

kubectl exec $pod -- /bin/bash -c "pkill $command"
kubectl exec $pod -- /bin/bash -c "echo after restart... >> operator.log"
kubectl exec $pod -- /bin/bash -c "KUBERNETES_SERVICE_HOST=$straggler KUBERNETES_SERVICE_PORT=6443 $command >> operator.log 2>&1 &"

