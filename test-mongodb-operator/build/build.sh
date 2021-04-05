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

docker build \
    --build-arg GIT_COMMIT=$GIT_COMMIT \
    --build-arg GIT_BRANCH=$GIT_BRANCH \
    --build-arg GO_LDFLAGS="$GO_LDFLAGS" \
    --no-cache \
    -t "${dockerrepo}/mongodb-operator:${dockertag}" -f build/Dockerfile .

docker push ${dockerrepo}/mongodb-operator:${dockertag}
