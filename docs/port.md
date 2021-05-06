## Port a new operator:
In general, you will need to fill the entries in https://github.com/sieve-project/sieve/blob/main/controllers.py and prepare some Dockerfile, build scripts, deploy scripts and test scripts.

### Build
The first thing is to be able to build the operator into a container image and make sure the operator can function well.
Oftentimes, you will find how to build the operator in the readme or developer documentation.
The image build command is often in their Makefile, and you can easily find the Dockerfile.
What you need to do is to slightly modify the Dockerfile to:
1. Set the initial CMD as `["sleep", "infinity"]`. See [zookeeper-operator](https://github.com/sieve-project/sieve/blob/1606d324c509f0d4841629e3107ce78cc0e324cb/test-zookeeper-operator/build/Dockerfile#L40).
2. Install bash (or other necessary tools for you) in the image. See [zookeeper-operator](https://github.com/sieve-project/sieve/blob/1606d324c509f0d4841629e3107ce78cc0e324cb/test-zookeeper-operator/build/Dockerfile#L38).
3. If the orignal Dockerfile sets some user account/permission stuff, remove them to make your life easier.

Besides, you need to prepare a `build.sh` which contains all the commands to build an image and push it to your docker repo.
As an example, here is the modified Dockerfile and `build.sh` for the [zookeeper-operator](https://github.com/sieve-project/sieve/tree/main/test-zookeeper-operator/build).
Your Dockerfile will replace the original one, and the `build.sh` will be run in the operator directory to build the image. These are done by `build.py`, and you only need to specify related entries in `controllers.py`. Instrumentation will also be automatically done by `build.py` according to the mode you specify.

### Deploy
The second step is to be able to deploy (or install) the (instrumented) operator in your kind cluster.
Sometimes manual deploy steps are clearly listed in the readme (e.g., https://github.com/pravega/zookeeper-operator#manual-deployment) and you just need to type them one by one,
while sometimes you need to read the developer documentation to find out how to deploy the operator.
Concretely, deploying the operator often requires to install the CRDs and related RBAC config. For example, `kubectl create -f deploy/crds` and `kubectl create -f deploy/default_ns/rbac.yaml` for the [zookeeper-operator](https://github.com/pravega/zookeeper-operator#manual-deployment).

For a new controller, you need to find the correct commands (and configs) to do the above.
Besides, you also need to modify the deployment config of the operator to do the following:
1. Add a label: `sonartag: YOUR_OPERATOR_NAME`. So sonar can later find the pod. See [zookeeper-operator](https://github.com/sieve-project/sieve/blob/b4abe83426d5e2f4564563effe6ea380ae2831b8/test-zookeeper-operator/deploy/default_ns/operator.yaml#L10).
2. Replace the operator image repo name with `${SONAR-DR}`, and replace the tag with `${SONAR-DT}`. So sonar can use correct repo and tag when running the tests. See [zookeeper-operator](https://github.com/sieve-project/sieve/blob/b4abe83426d5e2f4564563effe6ea380ae2831b8/test-zookeeper-operator/deploy/default_ns/operator.yaml#L21).
3. Specify env variables `KUBERNETES_SERVICE_HOST` and `KUBERNETES_SERVICE_PORT` and import configmap `sonar-testing-global-config` in the yaml file. See [zookeeper-operator](https://github.com/sieve-project/sieve-issue-only/blob/481de8a61b8362f96dbf0e46c8dfe150ae786fbd/test-zookeeper-operator/deploy/default_ns/operator.yaml#L39).

See https://github.com/sieve-project/sieve/blob/main/test-zookeeper-operator/deploy/default_ns/operator.yaml as a complete example.
After figuring out how to deploy the operator, write them down in `controllers.py` as the [zookeeper-operator](https://github.com/sieve-project/sieve/blob/32c003016cb95e05487b9609115efa6325a36606/controllers.py#L155).

### Test
The final step is to prepare the test workloads, and sonar learn mode will automatically generate the time-travel config for the workload. The workload is often simple -- create/delete/create some resources, scale down/up some resources, or disable/enable some features in the spec. See https://github.com/sieve-project/sieve/blob/main/test-zookeeper-operator/test/recreateZookeeperCluster.sh and https://github.com/sieve-project/sieve/blob/main/test-zookeeper-operator/test/scaleDownUpZookeeperCluster.sh as examples.
Note that it takes some time for the operator to process one command so we sleep for a while before each command. The sleep time is set empirically.
Operator usually runs more slowly in learning mode, so we sometimes set larger sleep time in learning mode as in [zookeeper-operator](https://github.com/sieve-project/sieve/blob/32c003016cb95e05487b9609115efa6325a36606/test-zookeeper-operator/test/recreateZookeeperCluster.sh#L6).
Try to run the vanilla operator to decide the sleep time here. It usually ranges from 30s to 1 min. We may later find a better way to decide the sleep time.

After writing the workload, register it in `controllers.py` like the [zookeeper-operator](https://github.com/sieve-project/sieve/blob/32c003016cb95e05487b9609115efa6325a36606/controllers.py#L53).
After that, build the learning mode images
```
python3 build.py -p kubernetes -m learn -d YOUR_DOCKER_REPO_NAME
python3 build.py -p YOUR_OPERATOR_NAME -m learn -d YOUR_DOCKER_REPO_NAME
```
Run the learning mode
```
python3 run.py -p YOUR_OPERATOR_NAME -m learn -t YOUR_TEST_NAME
```
You will get some config files generated by sonar in `log/YOUR_OPERATOR_NAME/YOUR_TEST_NAME/learn/generated-config`.
To test them all, run
```
python3 run.py -p YOUR_OPERATOR_NAME -t YOUR_TEST_NAME -b
```
to test one of them (which you think is more promising)
```
python3 run.py -p YOUR_OPERATOR_NAME -t YOUR_TEST_NAME -c YOUR_FAVOURITE_CONFIG
```
Usually, if you can see `[ERROR]` in stdout, it indicates a bug.

