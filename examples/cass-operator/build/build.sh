#!/bin/bash
set -x

go mod tidy
mage operator:clean
mage operator:buildDocker
