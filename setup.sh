#!/bin/bash

set -ex

raise_log_level() {
    node=$1
    docker exec $node bash -c "sed -i '/- kube-apiserver/ a\    - --v=4'  /etc/kubernetes/manifests/kube-apiserver.yaml"
    docker exec $node bash -c "sed -i '/- kube-scheduler/ a\    - --v=4'  /etc/kubernetes/manifests/kube-scheduler.yaml"
    docker exec $node bash -c "sed -i '/- kube-controller-manager/ a\    - --v=4'  /etc/kubernetes/manifests/kube-controller-manager.yaml"
    sleep 2
}

conf=$1
if [ -z "$conf" ]; then
    conf="kind.yaml"
fi

kind create cluster --image xudongs/node:latest --config $conf
docker exec kind-control-plane bash -c 'mkdir -p /root/.kube/ && cp /etc/kubernetes/admin.conf /root/.kube/config'
cd sonar-server
go build
cd ..
docker cp sonar-server kind-control-plane:/sonar-server
docker exec kind-control-plane bash -c 'cd /sonar-server && ./sonar-server &> sonar-server.log &'
# raise_log_level kind-control-plane
