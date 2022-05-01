#!/bin/bash

ytt -f config/ | kbld -f-
old_tag=$(docker images | grep kbld | awk '{print $2}')
echo $old_tag
docker tag kbld:$old_tag kapp-controller:latest
