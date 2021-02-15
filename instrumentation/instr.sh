#!/bin/bash

go build
./instrumentation $1 $2
