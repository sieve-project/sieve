#!/bin/bash

set -e

usage() { echo "$0 usage:" && grep " .)\ #" $0; exit 0; }


vanilla=false

cd app
OLDPWD=$PWD
GOPATH=/home/aishwarya/go

rm -rf zookeeper-operator
echo "cloning project..."
git clone https://github.com/pravega/zookeeper-operator.git
cd zookeeper-operator
git checkout -b sonar
cd $OLDPWD
if [ "$vanilla" = false ] ; then
	echo "installing the required lib..."
	go mod download sigs.k8s.io/controller-runtime@v0.4.0
	mkdir -p zookeeper-operator/dep-sonar/src/sigs.k8s.io
	cp -r ${GOPATH}/pkg/mod/sigs.k8s.io/controller-runtime@v0.4.0 zookeeper-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0
	chmod +w -R zookeeper-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0
	cp -r ../../sonar.client zookeeper-operator/dep-sonar/src/sonar.client

	echo "modifying go.mod..."
	echo "replace sigs.k8s.io/controller-runtime => ./dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0" >> zookeeper-operator/go.mod
	echo "require sonar.client v0.0.0" >> zookeeper-operator/go.mod
	echo "replace sonar.client => ./dep-sonar/src/sonar.client" >> zookeeper-operator/go.mod

	echo "require sonar.client v0.0.0" >> zookeeper-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0/go.mod
	echo "replace sonar.client => ../../sonar.client" >> zookeeper-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0/go.mod

	cd zookeeper-operator
	cd $OLDPWD

	echo "instrumenting the code..."
	cd ../../instrumentation/
	./instr.sh sparse-read ${OLDPWD}/zookeeper-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0
	cd $OLDPWD
fi

echo "replacing the Dockerfile and build.sh..."
cp hack/build.sh zookeeper-operator/build.sh
cp hack/Dockerfile zookeeper-operator/Dockerfile

echo "building the operator..."
cd zookeeper-operator
./build.sh
echo "built"
