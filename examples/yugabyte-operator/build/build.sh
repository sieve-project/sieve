#!/bin/bash
set -x

docker build \
    --no-cache \
    -t "yugabyte/yugabyte-operator:latest" -f build/Dockerfile .
