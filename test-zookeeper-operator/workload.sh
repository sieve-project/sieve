#!/bin/bash

set -ex

dir="log"
normal=false
while getopts ":d:n" arg; do
    case $arg in
        d) # Specify log directory.
        dir=${OPTARG}
        ;;
        n) # Test without instrumentation.
        normal=true
        ;;
        h | *) # Display help.
        usage
        ;;
    esac
done

mkdir -p $dir

cd ..
if [ "$normal" = false ] ; then
    cp config/sparse-read-zk.yaml sonar-server/server.yaml
else
    cp config/none.yaml sonar-server/server.yaml
fi
./teardown.sh
./setup.sh kind.yaml

cd zookeeper-operator
./bootstrap.sh
sleep 60s
kubectl cp ../config/none.yaml kube-apiserver-kind-control-plane:/sonar.yaml -n kube-system

operator=`kubectl get pods | grep zookeeper-operator | cut -f1 -d " "`
if [ "$normal" = false ] ; then
    kubectl cp ../config/sparse-read-zk.yaml $operator:/sonar.yaml
else
    kubectl cp ../config/none.yaml $operator:/sonar.yaml
fi
kubectl exec $operator -- /bin/bash -c "KUBERNETES_SERVICE_HOST=kind-control-plane KUBERNETES_SERVICE_PORT=6443 ./zookeeper-operator &> operator.log &"

kubectl create -f zk.yaml
sleep 200s
echo ">>> before cluster delete:" > $dir/stdout.log
kubectl get pods -o wide >> $dir/stdout.log
kubectl get pvc -o wide >> $dir/stdout.log

kubectl delete -f zk.yaml
sleep 150s
echo ">>> after cluster delete:" >> $dir/stdout.log
kubectl get pods -o wide >> $dir/stdout.log
kubectl get pvc -o wide >> $dir/stdout.log

kubectl logs kube-apiserver-kind-control-plane -n kube-system > $dir/apiserver.log
docker cp kind-control-plane:/sonar-server/sonar-server.log $dir/sonar-server.log
kubectl cp $operator:/operator.log $dir/operator.log
kubectl describe ZookeeperCluster > $dir/zkc.log

# cd ..
# ./teardown.sh
