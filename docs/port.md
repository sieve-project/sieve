## Port a new controller:
To facilitate Sieve testing, you will need to fill some entries in [controllers.py](../controllers.py) and provide steps to build and deploy the controller.

First of all, please create a `sieve_config.json` and specify the docker repo that you can push to:
```
{
    "docker_repo": "YOUR_REPO"
}
```
Sieve will push the controller and Kubernetes images to this repo.

Please also create the following directory for your controller (just like [examples/zookeeper-operator](../examples/zookeeper-operator)):
```
test-your-operator
  |- build
  |- deploy
  |- test
```
The necessary files for porting will be placed in the directory.

### Build
The first step is to make Sieve able to build the controller image.

You need to copy the `Dockerfile` (for building the controller image) to `test-your-operator/build`. You also need to ensure that the `Dockerfile` will copy the source files automatically added by Sieve. As an example, see the [`Dockerfile`](../examples/zookeeper-operator/build/Dockerfile#L17) we prepared for the zookeeper-operator.

Besides, you need to prepare a `build.sh` that builds the docker image and pushes to a remote docker repo in `test-your-operator/build`. The script should take two arguments: the first is the docker repo name and the second is the image tag.
As an example, refer to the [`build.sh`](../examples/zookeeper-operator/build/build.sh) we prepared for the zookeeper-operator.

After that, please fill in the following entries in [controllers.py](../controllers.py)
- `github_link`: github link to clone your controller
- `sha`: the commit of the controller you want to test
- `controller_runtime_version`: the version of the `controller_runtime` used by your controller
- `client_go_version`: the version of the `client_go` used by your controller
- `app_dir`: the location to clone the controller to
- `test_dir`: the directory you just created
- `docker_file`: the location of the `Dockerfile` in your controller repo

Now run `python3 build.py -p your-operator -m learn`. This command will instrument the controller (specifically `controller_runtime` and `client_go`), replace the original `Dockerfile` with the one you modified, build the controller image using the `build.sh` and push the image to your docker repo. The image will be used later.


### Deploy
The second step is to make Sieve able to deploy the controller in a kind cluster.

You need to copy the necessary files (for installing the controller deployment, CRDs and other resources) to `test-your-operator/deploy`.

You also need to modify the controller deployment a little bit so that Sieve can properly inject fault
- Add a label: `sievetag: YOUR_OPERATOR_NAME`. So sieve can find the pod during testing. See [this example](../examples/zookeeper-operator/deploy/default_ns/operator.yaml#L10).
- Set the controller image repo name to `${SIEVE-DR}`, and set the image tag to `${SIEVE-DT}`. So sieve can switch to different images when testing different bug patterns. See [this example](../examples/zookeeper-operator/deploy/default_ns/operator.yaml#L21).
- Import configmap `sieve-testing-global-config` as Sieve needs to pass some some configurations to the instrumented controller. See [this example](../examples/zookeeper-operator/deploy/default_ns/operator.yaml#L44).
- Specify env variables `KUBERNETES_SERVICE_HOST` and `KUBERNETES_SERVICE_PORT`. This is used for testing stale-stateing bugs. See [this example](../examples/zookeeper-operator/deploy/default_ns/operator.yaml#L39).
- Optional: Set `imagePullPolicy` to `IfNotPresent` (for CI run). See [this example](../examples/zookeeper-operator/deploy/default_ns/operator.yaml#L27)

After that, please define the function to deploy the controller in [controllers.py](../controllers.py) and fill the function in `deploy`. See the example `zookeeper_operator_deploy`.

Please also specify the following entries in [controllers.py](../controllers.py)
- `operator_pod_label`: the label of the controller pod you just specified. Sieve needs the information to find the pod during testing.

### Test
The last step is to prepare the test workloads and make Sieve able to run the test workload.

You can provide a bash script to start the test workload, or implement the test workload using our `test_framework` API (see the examples in `workloads.py`). Besides, please also copy any test-related files into `test-your-operator/test`.

After that, please fill in the entries in [controllers.py](../controllers.py)
- `test_setting`: the test workloads provided by you. You can also specify the number of apiservers and workers your controller needs.
- `CRDs`: the CRD managed by your controllers. Please ensure they are specified in lower-case. Sieve needs the information to learn the related events in learning stage.


Now you are all set.
To test your controllers, just build the image:
```
python3 build.py -p k8s -m all
python3 build.py -p your_operator -m all
```
First run Sieve learning stage
```
python3 sieve.py -p your_operator -t your_test_suite_name -s learn -m learn-twice
```
Sieve will learn the promising fault injection points for intermediate-states, unobserved-states and stale-stateing testing, and encode them into yaml files stored in `log/your_operator/your_test_suite_name/learn/learn-once/{intermediate-state, unobserved-states, stale-state}`.
If you want to test all the intermediate-state injection points, just run:
```
python3 sieve.py -p your_operator -t your_test_suite_name -s test -m atom-vio -b
```
to test one of the injection point:
```
python3 sieve.py -p your_operator -t your_test_suite_name -s test -m atom-vio -c path_to_your_injection_file
```
Sieve will report any bugs it find at the end of the testing.

