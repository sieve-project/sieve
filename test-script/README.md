## Run test configs in parallel on multiple workers

### How to run
1. Finish the learning mode and generate all the test configs on a master node(could be any worker node)
2. Create a file called `hosts` under this test-script directory and list all the node's address. Except for this master node, write `:` to indicate that this is a local node.
2. On this master node's test-script directory, run:  
    `bash runtest.sh`  
    If you want to pull from your own docker repo, modify the first step in the runtest.sh to add `-d ${DOCKERREPO}` to the python command.  

This shell script will
1. generate all the docker pull commands and test commands needed into files.
2. Run docker pull commands on all nodes
3. scp configs files to worker nodes
4. Run all tests in parallel on all the nodes

### Note
It assumes the sieve project home directory is under `/home/ubuntu`
