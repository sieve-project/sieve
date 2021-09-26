# Sieve: Testing datacenter infrastructures using partial histories

[![Kubernetes Image Build](https://github.com/sieve-project/sieve/actions/workflows/kubernetes.yml/badge.svg)](https://github.com/sieve-project/sieve/actions/workflows/kubernetes.yml)
[![Sieve Test](https://github.com/sieve-project/sieve/actions/workflows/sieve-test.yml/badge.svg)](https://github.com/sieve-project/sieve/actions/workflows/sieve-test.yml)
[![Sieve Daily Integration](https://github.com/sieve-project/sieve/actions/workflows/sieve-daily.yml/badge.svg)](https://github.com/sieve-project/sieve/actions/workflows/sieve-daily.yml)


## Requirements
* Docker daemon must be running (please ensure you can run `docker` commands without sudo)
* A docker repo that you have write access to
* [go1.13.9](https://golang.org/doc/devel/release#go1.13) installed and `$GOPATH` set
* [kind](https://kind.sigs.k8s.io/) installed and `$KUBECONFIG` set (our kind cluster uses Kubernetes v1.18.9 and etcd)
* python3 installed and the following packages installed
    * `kubernetes`, `docker`, `pyyaml`, `jsondiff`, `pysqlite3`, `py-cui`, `docker`, `jsondiff`, `deepdiff`
    * simply run `pip3 install -r requirements.txt` to install those packages
* [sqlite3](https://help.dreamhost.com/hc/en-us/articles/360028047592-Installing-a-custom-version-of-SQLite3) (>=3.32) installed

Note: sqlite3 is not required if you want to only reproduce the bugs.

To check for those requirements, you can simply run the following script on the project's root directory,
```shell
python3 check-env.py
```

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
