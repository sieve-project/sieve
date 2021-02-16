#!/bin/bash

set -ex

cd app
OLDPWD=$PWD

rm -rf cassandra-operator
git clone git@github.com:instaclustr/cassandra-operator.git
cd cassandra-operator
git checkout fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd
git checkout -b sonar
cd $OLDPWD

# install the required lib
go mod download sigs.k8s.io/controller-runtime@v0.4.0
mkdir -p cassandra-operator/dep-sonar/src/sigs.k8s.io
cp -r ${GOPATH}/pkg/mod/sigs.k8s.io/controller-runtime@v0.4.0 cassandra-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0
chmod +w -R cassandra-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0
cp -r ../../sonar.client cassandra-operator/dep-sonar/src/sonar.client

# modify go.mod
echo "replace sigs.k8s.io/controller-runtime => ./dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0" >> cassandra-operator/go.mod
echo "require sonar.client v0.0.0-00010101000000-000000000000" >> cassandra-operator/go.mod
echo "replace sonar.client => ./dep-sonar/src/sonar.client" >> cassandra-operator/go.mod

echo "require sonar.client v0.0.0-00010101000000-000000000000" >> cassandra-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0/go.mod
echo "replace sonar.client => ../../sonar.client" >> cassandra-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0/go.mod

cd cassandra-operator
git add -A && git commit -m "before instr"
cd $OLDPWD

# run the instrumentation tool
../../instrumentation/instr.sh sparse-read ${OLDPWD}/cassandra-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0

# replace the Dockerfile and build.sh
cp hack/build.sh cassandra-operator/build.sh
cp hack/Dockerfile cassandra-operator/docker/cassandra-operator/Dockerfile

# build the operator
cd cassandra-operator
./build.sh
