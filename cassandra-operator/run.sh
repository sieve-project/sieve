#!/bin/bash
set -x

workload=$1
if [ -z "$workload" ]; then workload=workload1.sh; fi

loops=$2
if [ -z "$loops" ]; then loops=1; fi

for i in $(seq 1 $loops); do ./$workload save/save-exp$i; done
