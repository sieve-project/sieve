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
dockerrepo=$2
dockertag=$3
if [ -z "$conf" ]; then
    exit 1
fi
if [ -z "$dockerrepo" ]; then
    exit 1
fi
if [ -z "$dockertag" ]; then
    exit 1
fi

kind create cluster --image ${dockerrepo}/node:${dockertag} --config $conf
docker exec kind-control-plane bash -c 'mkdir -p /root/.kube/ && cp /etc/kubernetes/admin.conf /root/.kube/config'
# cd sonar-server
# go mod tidy
# go build
# cd ..
# docker cp sonar-server kind-control-plane:/sonar-server
# docker exec kind-control-plane bash -c 'cd /sonar-server && ./sonar-server &> sonar-server.log &'
# raise_log_level kind-control-plane
