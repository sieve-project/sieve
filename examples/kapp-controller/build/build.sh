#!/bin/bash

echo "# sieve.client v0.0.0
## explicit; go 1.13
sieve.client" >> vendor/modules.txt

ytt -f config/ | kbld -f-
old_tag=$(docker images | grep kbld | awk '{print $2}')
echo $old_tag
docker tag kbld:$old_tag kapp-controller:latest
docker rmi kbld:$old_tag
