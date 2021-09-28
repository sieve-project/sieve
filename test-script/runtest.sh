#!/bin/bash
set -x

# 1. Generate test commands and docker pull commands
python3 gen_commands.py

# 2. Run docker pull commands on all nodes
#
# --onall - run the same commands on all worker nodes
parallel --ssh 'ssh -i "~/.ssh/id_rsa" ' \
         --sshloginfile hosts \
         --onall \
         --env PATH \
         < pull-commands.txt

# 3. scp configs files to worker nodes
parallel --ssh 'ssh -i "~/.ssh/id_rsa" ' \
	     'if [[ "{}" != ":" ]]; then scp -r ../log {}:/home/ubuntu/sieve; else {}; fi' \
	     < hosts

# 4. clean up previous run result in sieve_test_results
parallel --workdir '/home/ubuntu/sieve' \
         --ssh 'ssh -i "~/.ssh/id_rsa" ' \
         --sshloginfile hosts \
         --onall \
         ::: 'rm -rf ./sieve_test_results'

parallel --workdir '/home/ubuntu/sieve' \
         --ssh 'ssh -i "~/.ssh/id_rsa" ' \
         --sshloginfile hosts \
         --onall \
         ::: 'rm -rf ./log_save'

# 5. Run all tests in parallel
#
# workdir      - work directory on remote
# ssh          - specify idenity files for ssh
# sshloginfile - list of hosts
# progress     - show progress
# j 1          - one job on one machine each time
# results      - place to save output
# env          - which environment variable to inherit
parallel --workdir '/home/ubuntu/sieve' \
         --ssh 'ssh -i "~/.ssh/id_rsa" ' \
         --sshloginfile hosts \
         --progress \
         -j 1 \
         --results . \
         --env PATH \
         --env KUBECONFIG \
         --env GOPATH \
         < commands.txt

# 6. scp results back
parallel --ssh 'ssh -i "~/.ssh/id_rsa" ' \
	     'if [[ "{}" != ":" ]]; then scp -r {}:/home/ubuntu/sieve/sieve_test_results ../; else {}; fi' \
	     < hosts

parallel --ssh 'ssh -i "~/.ssh/id_rsa" ' \
	     'if [[ "{}" != ":" ]]; then scp -r {}:/home/ubuntu/sieve/log_save ../; else {}; fi' \
	     < hosts

now=$(data+"%Y-%m-%d")
mv ../log_save ./log_save_${now}

# 7. combine test results in sieve_test_results and save it
python3 combine_json.py