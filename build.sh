#!/bin/bash
set -ex
OLDPWD=$PWD
usage() { echo "$0 usage:" && grep " .)\ #" $0; exit 0; }

reuse='none'
mode='vanilla'
project='cassandra-operator'
sha='none'

install_and_import() {
  if [ $project = 'cassandra-operator' ]; then
    echo "installing the required lib..."
    go mod download sigs.k8s.io/controller-runtime@v0.4.0 >> /dev/null
    mkdir -p app/cassandra-operator/dep-sonar/src/sigs.k8s.io
    cp -r ${GOPATH}/pkg/mod/sigs.k8s.io/controller-runtime@v0.4.0 app/cassandra-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0
    chmod +w -R app/cassandra-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0
    cp -r sonar.client app/cassandra-operator/dep-sonar/src/sonar.client

    echo "modifying go.mod..."
    echo "replace sigs.k8s.io/controller-runtime => ./dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0" >> app/cassandra-operator/go.mod
    echo "require sonar.client v0.0.0" >> app/cassandra-operator/go.mod
    echo "replace sonar.client => ./dep-sonar/src/sonar.client" >> app/cassandra-operator/go.mod

    echo "require sonar.client v0.0.0" >> app/cassandra-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0/go.mod
    echo "replace sonar.client => ../../sonar.client" >> app/cassandra-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0/go.mod

    echo "replacing the Dockerfile and build.sh..."
    cp test-cassandra-operator/build/build.sh app/cassandra-operator/build.sh
    cp test-cassandra-operator/build/Dockerfile app/cassandra-operator/docker/cassandra-operator/Dockerfile

    cd app/cassandra-operator
    git add -A >> /dev/null
    git commit -m "before instr" >> /dev/null
    cd $OLDPWD
  fi
}

instrument() {
  cd instrumentation
  if [ $mode = 'sparse-read' ]; then
    if [ $project = 'cassandra-operator' ]; then
      ./instr.sh $mode ${OLDPWD}/fakegopath/src/k8s.io/kubernetes ${OLDPWD}/app/cassandra-operator/dep-sonar/src/sigs.k8s.io/controller-runtime@v0.4.0
    fi
  elif [ $mode = 'time-travel' ]; then
    ./instr.sh $mode ${OLDPWD}/fakegopath/src/k8s.io/kubernetes
  fi

  cd $OLDPWD
}

while getopts ":m:p:r:s:" arg; do
    case $arg in
        r) # Reuse the existing kubernetes and controller code: none or all.
        reuse=${OPTARG}
        ;;
        m) # Specify the mode: vanilla, sparse-read or time-travel.
        mode=${OPTARG}
        ;;
        p) # Specify the project to test: cassandra-operator or zookeeper-operator.
        project=${OPTARG}
        if [ $project = 'cassandra-operator' ]; then
          sha='fe8f91da3cd8aab47f21f7a3aad4abc5d4b6a0dd'
        fi
        ;;
        s) # Specify the commit ID of the project
        sha=${OPTARG}
        ;;
        h | *) # Display help.
        usage
        ;;
    esac
done

echo "reuse: $reuse mode: $mode project: $project"

if [ $reuse = 'none' ]; then
  # download new k8s code
  rm -rf fakegopath
  echo "cloning Kubernetes..."
  mkdir -p fakegopath/src/k8s.io
  git clone --single-branch --branch v1.18.9 git@github.com:kubernetes/kubernetes.git fakegopath/src/k8s.io/kubernetes
  cd fakegopath/src/k8s.io/kubernetes
  git checkout -b sonar >> /dev/null
  cd $OLDPWD

  # import sonar.client into k8s
  echo "require sonar.client v0.0.0" >> fakegopath/src/k8s.io/kubernetes/staging/src/k8s.io/apiserver/go.mod
  echo "replace sonar.client => ../../sonar.client" >> fakegopath/src/k8s.io/kubernetes/staging/src/k8s.io/apiserver/go.mod
  cp -r sonar.client fakegopath/src/k8s.io/kubernetes/staging/src/sonar.client
  ln -s ../staging/src/sonar.client fakegopath/src/k8s.io/kubernetes/vendor/sonar.client

  # download new controller code
  rm -rf app/$project
  echo "cloning $project..."
  git clone git@github.com:instaclustr/${project}.git app/$project >> /dev/null
  cd app/$project
  git checkout $sha >> /dev/null
  git checkout -b sonar >> /dev/null
  cd $OLDPWD

  # install libs and import sonar.client into controller
  install_and_import

  # instrument k8s and controller code according to the mode
  instrument
fi

# build kind image
cd fakegopath/src/k8s.io/kubernetes
GOPATH=${OLDPWD}/fakegopath KUBE_GIT_VERSION=v1.18.9-sr-`git rev-parse HEAD` kind build node-image
cd $OLDPWD
docker build --no-cache -t xudongs/node:latest .

# build controller image
echo "building the operator..."
cd app/$project
./build.sh

