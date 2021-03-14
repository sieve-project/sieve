#!/bin/bash

set -ex


host_bypass_balancer() {
    sed -i "s/127.0.0.1:$1/127.0.0.1:$2/g" $KUBECONFIG
}

api_port=`docker ps|grep kind-control-plane'$'|cut -d':' -f 3|cut -d'-' -f1`
balancer_port=`docker ps|grep kind-external-load-balancer'$' |cut -d':' -f 3|cut -d'-' -f1`
host_bypass_balancer $balancer_port $api_port
