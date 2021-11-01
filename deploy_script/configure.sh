#!/bin/bash
ansible-playbook docker.yaml -i ansible_hosts
ansible-playbook go.yaml -i ansible_hosts
ansible-playbook python.yaml -i ansible_hosts
ansible-playbook kind.yaml -i ansible_hosts
ansible-playbook kubectl.yaml -i ansible_hosts
ansible-playbook helm.yaml -i ansible_hosts
