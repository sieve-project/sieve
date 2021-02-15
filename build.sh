#!/bin/bash
set -ex

mode=$1
if [ -z "$mode" ]; then
    mode="vanilla"
fi

echo "build mode: $mode..."

if [[ "$mode" == "instr" ]]; then
  # instrument k8s and install sonar lib
  # instrument is not automated yet
  cd $GOPATH/src/k8s.io/kubernetes
  cd staging/src
  rm -rf github.com
  cp -r $GOPATH/src/github.com/xlab-uiuc/sonar-lib/github.com/ github.com

  cd $GOPATH/src/k8s.io/kubernetes
  cd vendor/github.com
  ln -s ../../staging/src/github.com/xlab-uiuc/  xlab-uiuc
fi

# build kind image
cd $GOPATH/src/k8s.io/kubernetes
KUBE_GIT_VERSION=v1.18.9-sr-`git rev-parse HEAD` kind build node-image
# build another image wrapping around the kind image for better utility
cd sonar
docker build --no-cache -t xudongs/node:latest .
