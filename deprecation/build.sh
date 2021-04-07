#!/bin/bash
set -e
usage() { echo "$0 usage:" && grep " .)\ #" $0; exit 0; }

OLDPWD=$PWD
reuse='none'
mode='vanilla'
project='none'
sha='none'
crversion=${CRV}
cgversion=${CGV}
githublink=${GL}
dockerfile=${DF}
dockerrepo=${DR}
dockertag=${DT}

install_and_import() {
  echo "installing the required lib..."
  go mod download sigs.k8s.io/controller-runtime${crversion} >> /dev/null
  mkdir -p app/${project}/dep-sonar/src/sigs.k8s.io
  cp -r ${GOPATH}/pkg/mod/sigs.k8s.io/controller-runtime${crversion} app/${project}/dep-sonar/src/sigs.k8s.io/controller-runtime${crversion}
  chmod +w -R app/${project}/dep-sonar/src/sigs.k8s.io/controller-runtime${crversion}
  cp -r sonar-client app/${project}/dep-sonar/src/sonar.client
  if [ $mode = 'learn' ]; then
    go mod download k8s.io/client-go${cgversion} >> /dev/null
    mkdir -p app/${project}/dep-sonar/src/k8s.io
    cp -r ${GOPATH}/pkg/mod/k8s.io/client-go${cgversion} app/${project}/dep-sonar/src/k8s.io/client-go${cgversion}
    chmod +w -R app/${project}/dep-sonar/src/k8s.io/client-go${cgversion}
  fi
  cd app/${project}
  git add -A >> /dev/null
  git commit -m "download the lib" >> /dev/null
  cd $OLDPWD

  echo "modifying go.mod..."
  echo "replace sigs.k8s.io/controller-runtime => ./dep-sonar/src/sigs.k8s.io/controller-runtime${crversion}" >> app/${project}/go.mod
  echo "require sonar.client v0.0.0" >> app/${project}/go.mod
  echo "replace sonar.client => ./dep-sonar/src/sonar.client" >> app/${project}/go.mod
  echo "require sonar.client v0.0.0" >> app/${project}/dep-sonar/src/sigs.k8s.io/controller-runtime${crversion}/go.mod
  echo "replace sonar.client => ../../sonar.client" >> app/${project}/dep-sonar/src/sigs.k8s.io/controller-runtime${crversion}/go.mod
  if [ $mode = 'learn' ]; then
    echo "replace k8s.io/client-go => ./dep-sonar/src/k8s.io/client-go${cgversion}" >> app/${project}/go.mod
    echo "replace k8s.io/client-go => ../../k8s.io/client-go${cgversion}" >> app/${project}/dep-sonar/src/sigs.k8s.io/controller-runtime${crversion}/go.mod
    echo "require sonar.client v0.0.0" >> app/${project}/dep-sonar/src/k8s.io/client-go${cgversion}/go.mod
    echo "replace sonar.client => ../../sonar.client" >> app/${project}/dep-sonar/src/k8s.io/client-go${cgversion}/go.mod
  fi

  echo "replacing the Dockerfile and build.sh..."
  cp test-${project}/build/build.sh app/${project}/build.sh
  cp test-${project}/build/Dockerfile app/${project}/${dockerfile}
  cd app/${project}
  git add -A >> /dev/null
  git commit -m "import the lib" >> /dev/null
  cd $OLDPWD
}

instrument() {
  cd instrumentation
  go build
  if [ $mode = 'sparse-read' ]; then
    ./instrumentation $project $mode ${OLDPWD}/app/${project}/dep-sonar/src/sigs.k8s.io/controller-runtime${crversion}
  elif [ $mode = 'time-travel' ]; then
    ./instrumentation $project $mode ${OLDPWD}/app/${project}/dep-sonar/src/sigs.k8s.io/controller-runtime${crversion} ${OLDPWD}/fakegopath/src/k8s.io/kubernetes
  elif [ $mode = 'learn' ]; then
    ./instrumentation $project $mode ${OLDPWD}/app/${project}/dep-sonar/src/sigs.k8s.io/controller-runtime${crversion} ${OLDPWD}/app/${project}/dep-sonar/src/k8s.io/client-go${cgversion}
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

set -ex
if [ $project = 'kubernetes' ]; then
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
  cp -r sonar-client fakegopath/src/k8s.io/kubernetes/staging/src/sonar.client
  ln -s ../staging/src/sonar.client fakegopath/src/k8s.io/kubernetes/vendor/sonar.client

  # instrument k8s
  instrument

  # build kind image
  cd fakegopath/src/k8s.io/kubernetes
  GOPATH=${OLDPWD}/fakegopath KUBE_GIT_VERSION=v1.18.9-sr-`git rev-parse HEAD` kind build node-image
  cd $OLDPWD
  docker build --no-cache -t ${dockerrepo}/node:${dockertag} .
else
  # download new controller code
  rm -rf app/$project
  echo "cloning $project..."
  git clone ${githublink} app/${project} >> /dev/null
  cd app/$project
  git checkout $sha >> /dev/null
  git checkout -b sonar >> /dev/null
  cd $OLDPWD

  # install libs and import sonar.client into controller
  install_and_import

  # instrument controller liberaries
  instrument

  # build controller image
  echo "building the operator..."
  cd app/$project
  ./build.sh ${dockerrepo} ${dockertag}
fi

