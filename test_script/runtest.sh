#!/bin/bash
set -x

# 1. Delete all old docker images
parallel --workdir '/home/ubuntu/sieve' \
         --ssh 'ssh -i "~/.ssh/id_rsa" ' \
         --sshloginfile hosts \
         --onall \
         ::: 'docker system prune -a'

# 2. Generate test commands and docker pull commands
python3 runlearn.py  # [-p projects]
python3 gen_commands.py  # [-p projects]

# 3. Run docker pull commands on all nodes
#
# --onall - run the same commands on all worker nodes
parallel --ssh 'ssh -i "~/.ssh/id_rsa" ' \
         --sshloginfile hosts \
         --onall \
         --env PATH \
         < pull-commands.txt

# 4. scp configs files to worker nodes
parallel --ssh 'ssh -i "~/.ssh/id_rsa" ' \
	     'if [[ "{}" != ":" ]]; then scp -r ../log {}:/home/ubuntu/sieve; else {}; fi' \
	     < hosts

# 5. clean up previous run result in sieve_test_results
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
         --ssh 'ssh -i "~/.ssh/id_rsa" ' \
         --sshloginfile hosts \
         --progress \
         -j 1 \
         --results . \
         --env PATH \
         --env KUBECONFIG \
         --env GOPATH \
         < commands.txt

# 7. scp results back
parallel --ssh 'ssh -i "~/.ssh/id_rsa" ' \
	     'if [[ "{}" != ":" ]]; then scp -r {}:/home/ubuntu/sieve/sieve_test_results ../; else {}; fi' \
	     < hosts

parallel --ssh 'ssh -i "~/.ssh/id_rsa" ' \
	     'if [[ "{}" != ":" ]]; then scp -r {}:/home/ubuntu/sieve/log ../; else {}; fi' \
	     < hosts

now=$(date +"%Y-%m-%d")
mv ../log ./log_save_${now}

# 8. combine test results in sieve_test_results and save it
python3 combine_json.py

# 9. Clean up after massive testing
parallel --workdir '/home/ubuntu/sieve' \
         --ssh 'ssh -i "~/.ssh/id_rsa" ' \
         --sshloginfile hosts \
         --onall \
         ::: 'rm -rf ./log'


parallel --workdir '/home/ubuntu/sieve' \
         --ssh 'ssh -i "~/.ssh/id_rsa" ' \
         --sshloginfile hosts \
         --onall \
         --env PATH \
         --env KUBECONFIG \
         --env GOPATH \
         ::: 'kind delete cluster'
