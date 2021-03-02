#!/bin/bash

set -e

usage() { echo "$0 usage:" && grep " .)\ #" $0; exit 0; }

sha='fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd'
vanilla=false

while getopts ":s:v" arg; do
    case $arg in
        s) # Specify git commit ID (sha) of the project.
        sha=${OPTARG}
        ;;
        v) # Test without instrumentation.
        vanilla=true
        ;;
        h | *) # Display help.
        usage
        ;;
    esac
done

echo "sha is $sha and vanilla is $vanilla"

cd app
OLDPWD=$PWD

rm -rf cassandra-operator
echo "cloning project..."
git clone git@github.com:instaclustr/cassandra-operator.git >> /dev/null
cd cassandra-operator
git checkout $sha >> /dev/null
git checkout -b sonar >> /dev/null
cd $OLDPWD

if [ "$vanilla" = false ] ; then
    echo "installing the required lib..."
    go mod download sigs.k8s.io/controller-runtime@v0.4.0 >> /dev/null
    mkdir -p cassandra-operator/dep-sonar/src/sigs.k8s.io
    cp -r ${GOPATH}/pkg/mod/sigs.k8s.io/controller-runtime@v0.4.0 cassandra-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0
    chmod +w -R cassandra-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0
    cp -r ../../sonar.client cassandra-operator/dep-sonar/src/sonar.client

    echo "modifying go.mod..."
    echo "replace sigs.k8s.io/controller-runtime => ./dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0" >> cassandra-operator/go.mod
    echo "require sonar.client v0.0.0" >> cassandra-operator/go.mod
    echo "replace sonar.client => ./dep-sonar/src/sonar.client" >> cassandra-operator/go.mod

    echo "require sonar.client v0.0.0" >> cassandra-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0/go.mod
    echo "replace sonar.client => ../../sonar.client" >> cassandra-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0/go.mod

    cd cassandra-operator
    git add -A >> /dev/null
    git commit -m "before instr" >> /dev/null
    cd $OLDPWD

    echo "instrumenting the code..."
    cd ../../instrumentation/
    ./instr.sh sparse-read ${OLDPWD}/cassandra-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0
    cd $OLDPWD
fi

echo "replacing the Dockerfile and build.sh..."
cp hack/build.sh cassandra-operator/build.sh
cp hack/Dockerfile cassandra-operator/docker/cassandra-operator/Dockerfile

echo "building the operator..."
cd cassandra-operator
./build.sh
echo "built"
