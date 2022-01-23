#!/bin/bash
set -x

dockerrepo=$1
dockertag=$2
if [ -z "$dockerrepo" ]; then
    exit 1
fi
if [ -z "$dockertag" ]; then
    exit 1
fi


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
$BUILD_IMAGE /bin/bash -c "operator-sdk build ${dockerrepo}/casskop-operator:${dockertag}  \
 && chmod -R 777 build/_output/"


# /usr/bin/env PUSHLATEST=true BUILD_IMAGE=laphets/casskop-build make docker-build
# docker tag orangeopensource/casskop:latest ${dockerrepo}/casskop-operator:${dockertag}
