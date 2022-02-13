#!/bin/bash
set -x

sed -i 's/go-generate generate-config-file /go-generate/g'  Makefile
OPERATOR_IMAGE=elastic/elastic-operator:latest make docker-build
