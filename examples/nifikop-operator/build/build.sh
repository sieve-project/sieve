#!/bin/bash
set -x

docker build \
    --no-cache \
    -t "orangeopensource/nifikop-operator:latest" -f Dockerfile .
