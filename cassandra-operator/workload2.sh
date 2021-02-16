#!/bin/bash

set -ex

dir=$1
if [ -z "$dir" ]; then
    dir="save"
fi
mkdir -p $dir

cd ..
cp config/staleness.yaml sonar-server/server.yaml
./setup.sh kind-ha.yaml

cd cassandra-operator
./bootstrap.sh
sleep 60s
operator=`kubectl get pods | grep cassandra-operator | cut -f1 --delimiter=" "`
kubectl cp ../config/staleness.yaml kube-apiserver-kind-control-plane2:/sonar.yaml -n kube-system
kubectl exec $operator -- /bin/bash -c "KUBERNETES_SERVICE_HOST=kind-control-plane KUBERNETES_SERVICE_PORT=6443 ./cassandra-operator &> operator1.log &"

kubectl apply -f cdc-1.yaml
sleep 150s
echo ">>> after create cdc:" > $dir/stdout.log
kubectl get pods -o wide >> $dir/stdout.log
kubectl get pvc -o wide >> $dir/stdout.log
echo " " >> $dir/stdout.log

kubectl delete CassandraDataCenter sonarcassandradatacenter
sleep 50s
echo ">>> after delete cdc:" >> $dir/stdout.log
kubectl get pods -o wide >> $dir/stdout.log
kubectl get pvc -o wide >> $dir/stdout.log
echo " " >> $dir/stdout.log

kubectl apply -f cdc-1.yaml
sleep 150s
echo ">>> after create cdc again:" >> $dir/stdout.log
kubectl get pods -o wide >> $dir/stdout.log
kubectl get pvc -o wide >> $dir/stdout.log
echo " " >> $dir/stdout.log

kubectl exec $operator -- /bin/bash -c "pkill ./cassandra-operator"
kubectl exec $operator -- /bin/bash -c "KUBERNETES_SERVICE_HOST=kind-control-plane2 KUBERNETES_SERVICE_PORT=6443 ./cassandra-operator &> operator2.log &"
sleep 30s
echo ">>> after restart controller and bind to apiserver2:" >> $dir/stdout.log
kubectl get pods -o wide >> $dir/stdout.log
kubectl get pvc -o wide >> $dir/stdout.log
echo " " >> $dir/stdout.log

kubectl logs kube-apiserver-kind-control-plane -n kube-system > $dir/apiserver1.log
kubectl logs kube-apiserver-kind-control-plane2 -n kube-system > $dir/apiserver2.log
kubectl cp $operator:/operator1.log $dir/operator1.log
kubectl cp $operator:/operator2.log $dir/operator2.log
docker cp kind-control-plane:/sonar-server/sonar-server.log $dir/sonar-server.log
kubectl describe CassandraDataCenter sonarcassandradatacenter > $dir/cdc.log

cd ..
./teardown.sh
