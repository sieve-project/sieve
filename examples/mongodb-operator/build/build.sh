#!/bin/bash
set -x

docker build \
    --build-arg GIT_COMMIT=$GIT_COMMIT \
    --build-arg GIT_BRANCH=$GIT_BRANCH \
    --build-arg GO_LDFLAGS="$GO_LDFLAGS" \
    --no-cache \
    -t "percona/mongodb-operator:latest" -f build/Dockerfile .
