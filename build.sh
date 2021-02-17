#!/bin/bash
set -ex
OLDPWD=$PWD
mode=$1
if [ -z "$mode" ]; then mode="vanilla"; fi

echo "build mode: $mode..."
rm -rf fakegopath
# install kubernetes v1.18.9 if not exist
if [ ! -d "fakegopath/src/k8s.io/kubernetes" ]
then
  mkdir -p fakegopath/src/k8s.io
  git clone --single-branch --branch v1.18.9 git@github.com:kubernetes/kubernetes.git fakegopath/src/k8s.io/kubernetes
  cd fakegopath/src/k8s.io/kubernetes
  git checkout -b sonar
  cd $OLDPWD
fi

if [[ "$mode" == "instr" ]]
then
  # instrument k8s and install sonar lib
  cd instrumentation
  ./instr.sh staleness ${OLDPWD}/fakegopath/src/k8s.io/kubernetes
  cd $OLDPWD

  rm -rf fakegopath/src/k8s.io/kubernetes/staging/src/sonar.client
  rm -f fakegopath/src/k8s.io/kubernetes/vendor/sonar.client

  echo "require sonar.client v0.0.0" >> fakegopath/src/k8s.io/kubernetes/staging/src/k8s.io/apiserver/go.mod
  echo "replace sonar.client => ../../sonar.client" >> fakegopath/src/k8s.io/kubernetes/staging/src/k8s.io/apiserver/go.mod

  cp -r sonar.client fakegopath/src/k8s.io/kubernetes/staging/src/sonar.client
  ln -s ../staging/src/sonar.client fakegopath/src/k8s.io/kubernetes/vendor/sonar.client
fi

# build kind image
cd fakegopath/src/k8s.io/kubernetes
GOPATH=${OLDPWD}/fakegopath KUBE_GIT_VERSION=v1.18.9-sr-`git rev-parse HEAD` kind build node-image

# build another image wrapping around the kind image for better utility
cd $OLDPWD
docker build --no-cache -t xudongs/node:latest .
