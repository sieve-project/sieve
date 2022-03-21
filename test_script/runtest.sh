#!/bin/bash
set -ex

# 0. Git pull sieve on all worker nodes
parallel --workdir '/home/ubuntu/sieve' \
         --sshloginfile remotehosts \
         --onall \
         ::: 'git pull'

# 1. Delete all old docker images
parallel --workdir '/home/ubuntu/sieve' \
         --sshloginfile hosts \
         --onall \
         ::: 'docker system prune -a'

# 2. Generate test commands and docker pull commands
rm -rf ../log
python3 runlearn.py -p $1
python3 gen_commands.py -p $1

# 3. Run docker pull commands on all nodes
#
# --onall - run the same commands on all worker nodes
parallel --sshloginfile hosts \
         --onall \
         --env PATH \
         < pull-commands.txt

# 4. scp configs files to worker nodes
parallel 'if [[ "{}" != ":" ]]; then scp -r ../log {}:/home/ubuntu/sieve; else {}; fi' \
	     < hosts

# 5. clean up previous run result in sieve_test_results
parallel --workdir '/home/ubuntu/sieve' \
         --sshloginfile hosts \
         --onall \
         ::: 'rm -rf ./sieve_test_results'

# 6. Run all tests in parallel
#
# workdir      - work directory on remote
# ssh          - specify idenity files for ssh
# sshloginfile - list of hosts
# progress     - show progress
# j 1          - one job on one machine each time
# results      - place to save output
# env          - which environment variable to inherit
parallel --workdir '/home/ubuntu/sieve' \
         --sshloginfile hosts \
         --progress \
         -j 1 \
         --results . \
         --env PATH \
         --env KUBECONFIG \
         --env GOPATH \
         < commands.txt

# 7. scp results back
parallel 'if [[ "{}" != ":" ]]; then scp -r {}:/home/ubuntu/sieve/sieve_test_results ../; else {}; fi' \
	     < hosts

parallel 'if [[ "{}" != ":" ]]; then scp -r {}:/home/ubuntu/sieve/log ../; else {}; fi' \
	     < hosts

now=$(date +"%Y-%m-%d")
mkdir -p ./massive-testing-${now}
cp -r ../sieve_test_results ./massive-testing-${now}
cp -r ../log ./massive-testing-${now}

# 8. combine test results in sieve_test_results and save it
python3 combine_json.py

# 9. Clean up after massive testing
parallel --workdir '/home/ubuntu/sieve' \
         --sshloginfile hosts \
         --onall \
         ::: 'rm -rf ./log'


parallel --workdir '/home/ubuntu/sieve' \
         --sshloginfile hosts \
         --onall \
         --env PATH \
         --env KUBECONFIG \
         --env GOPATH \
         ::: 'kind delete cluster'
