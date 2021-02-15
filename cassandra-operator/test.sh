#!/bin/bash

set -ex

dir=$1
if [ -z "$dir" ]; then
    dir="save"
fi
mkdir -p $dir

cd ..
./setup.sh kind-ha.yaml

cd cassandra-operator
./bootstrap.sh
sleep 60s
operator=`kubectl get pods | grep cassandra-operator | cut -f1 --delimiter=" "`
kubectl exec $operator -- /bin/bash -c "printenv"
kubectl exec $operator -- /bin/bash -c "./cassandra-operator &> operator.log &"
sleep 30s

# kubectl exec $operator -- /bin/bash -c "pkill ./cassandra-operator"
kubectl delete pod $operator
sleep 30s
operator=`kubectl get pods | grep cassandra-operator | cut -f1 --delimiter=" "`
kubectl exec $operator -- /bin/bash -c "./cassandra-operator &> operator.log &"
sleep 30s

# kubectl exec $operator -- /bin/bash -c "pkill ./cassandra-operator"
kubectl delete pod $operator
sleep 30s
operator=`kubectl get pods | grep cassandra-operator | cut -f1 --delimiter=" "`
kubectl exec $operator -- /bin/bash -c "./cassandra-operator &> operator.log &"
sleep 30s

kubectl logs kube-apiserver-kind-control-plane -n kube-system > $dir/apiserver.log
kubectl logs kube-apiserver-kind-control-plane2 -n kube-system > $dir/apiserver2.log
kubectl logs kube-apiserver-kind-control-plane3 -n kube-system > $dir/apiserver3.log
docker cp kind-control-plane:/sonar-server/sonar-server.log $dir/sonar-server.log

cd ..
./teardown.sh
