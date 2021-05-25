# Sieve: Testing datacenter infrastructures using partial histories

## Requirements
* Docker daemon must be running
* A docker repo that you have write access to
* go1.13 installed and `$GOPATH` set
* [kind](https://kind.sigs.k8s.io/) installed and `$KUBECONFIG` set
* [sqlite3](https://help.dreamhost.com/hc/en-us/articles/360028047592-Installing-a-custom-version-of-SQLite3) (>=3.32) installed
* python3 installed and `sqlite3`, `kubernetes` and `pyyaml` installed
    * `pip3 install pysqlite3`
    * `pip3 install kubernetes`
    * `pip3 install pyyaml`

## Demo:
Please refer to https://github.com/sieve-project/sieve/blob/main/docs/demo.md

## Bugs found by sieve:
Please refer to https://github.com/sieve-project/sieve/blob/main/docs/bugs.md

## Bug reproduction:
Please refer to https://github.com/sieve-project/sieve/blob/main/docs/reprod.md

## Port a new operator:
Please refer to https://github.com/sieve-project/sieve/blob/main/docs/port.md

## References:
You can learn more about Sieve from the following research paper:
* [**Reasoning about modern datacenter infrastructures using partial histories**](https://github.com/sieve-project/sieve/blob/main/docs/paper-hotos.pdf) <br>
Xudong Sun, Lalith Suresh, Aishwarya Ganesan, Ramnatthan Alagappan, Michael Gasch, Lilia Tang, and Tianyin Xu. To appear, In Proceedings of the 18th Workshop on Hot Topics in Operating Systems (HotOS-XVIII), Virtual Event, May 2021.
