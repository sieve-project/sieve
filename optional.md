We provide optional instructions to (1) [reproduce 8 indirect bugs](#optional-reproducing-8-indirect-bugs-1-hour) and (2) [generate controller trace](#optional-generating-controller-trace-and-test-plans-8-hours)

### Optional: Reproducing 8 indirect bugs (~1 hour)
To reproduce the 8 indirect bugs, please run
```
python3 reproduce_bugs.py -p all -b indirect
```
It will take about 1 hour to finish.
After it finishes, you will find a `bug_reproduction_stats.tsv` with the expected content as follows:
```
controller	bug	reproduced	test-result-file
cassandra-operator	indirect-1	True	sieve_test_results/cassandra-operator-scaledown-scaleup-cassandra-operator-indirect-1.yaml.json
cassandra-operator	indirect-2	True	sieve_test_results/cassandra-operator-scaledown-scaleup-brittle-cassandra-operator-indirect-2.yaml.json
mongodb-operator	indirect-1	True	sieve_test_results/mongodb-operator-disable-enable-shard-mongodb-operator-indirect-1.yaml.json
mongodb-operator	indirect-2	True	sieve_test_results/mongodb-operator-recreate-mongodb-operator-indirect-2.yaml.json
mongodb-operator	indirect-3	True	sieve_test_results/mongodb-operator-disable-enable-shard-brittle-mongodb-operator-indirect-3.yaml.json
yugabyte-operator	indirect-1	True	sieve_test_results/yugabyte-operator-disable-enable-tuiport-yugabyte-operator-indirect-1.yaml.json
yugabyte-operator	indirect-2	True	sieve_test_results/yugabyte-operator-disable-enable-tls-yugabyte-operator-indirect-2.yaml.json
zookeeper-operator	indirect-1	True	sieve_test_results/zookeeper-operator-recreate-zookeeper-operator-indirect-1.yaml.json
```

Note that it is normal to see some of the bugs are not reproduced by a single run because Sieve does NOT guarantee to consistently reproduce the 8 indirect bugs as we claimed in the paper.

Optionally, you can refer to https://github.com/sieve-project/sieve/blob/osdi-ae/reproducing_indirect_bugs.md for more detailed information about reproducing each bug.

### Optional: Generating controller trace and test plans (~8 hours)
To generate the controller trace (by running the test workloads) and further generate and reduce the test plans from the trace, please run
```
python3 reproduce_test_plan_generation.py --log=log --phase=all --times=twice
```
It will take about 8 hours.
After it finishes, you will find a `test_plan_stats.tsv` with similar results as we show in https://github.com/sieve-project/sieve/tree/osdi-ae#reproducing-figure-8-15-minutes.

Note that the newly generated `test_plan_stats.tsv` can be slightly different from the one in https://github.com/sieve-project/sieve/tree/osdi-ae#reproducing-figure-8-15-minutes as the controller traces are nondeterministic and can be different even for the same workload across different runs. For example, the number of events received by a controller can be different, which will further affect the number of generated test plans slightly.
