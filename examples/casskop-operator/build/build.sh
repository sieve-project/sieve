#!/bin/bash
set -x

BUILD_IMAGE=ghcr.io/sieve-project/sieve/casskop-build:v0.18.0-forked-pr317
WORKDIR=/go/casskop

echo "Generate zzz-deepcopy objects"
docker run --rm -v $(pwd):$WORKDIR  \
     --env GO111MODULE=on \
     \
    $BUILD_IMAGE /bin/bash -c 'operator-sdk generate k8s'

echo "Generate crds"
docker run --rm -v $(pwd):$WORKDIR  \
     --env GO111MODULE=on \
     \
    $BUILD_IMAGE /bin/bash -c 'operator-sdk generate crds'
sed -i '/\- protocol/d' deploy/crds/db.orange.com_cassandraclusters_crd.yaml
cp -v deploy/crds/* helm/*/crds/
cp -v deploy/crds/* */helm/*/crds/


echo "Build Cassandra Operator. Using cache from "$(go env GOCACHE)
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v $(pwd):$WORKDIR \
  \
--env GO111MODULE=on  \
$BUILD_IMAGE /bin/bash -c "operator-sdk build orangeopensource/casskop-operator:latest  \
 && chmod -R 777 build/_output/"
