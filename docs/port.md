## Port a new controller:
To port a controller, please first run `python3 start_porting.py your-controller`.
It will create a folder like this
```
examples/
  |- your-controller/
    |- config.json
    |- build/
      |- build.sh  
    |- deploy/
      |- deploy.sh
    |- oracle/
    |- test/
```
It takes four steps to port a controller:
1. provide the Dockerfile and necessary steps to build the controller in `build.sh`
2. provide the necessary files to deploy the controller and the steps to deploy in `deploy.sh`
3. provide test workloads
4. fill in the `config.json`

### Build
The first step is to make Sieve able to instrument and build the controller image.

Sieve's instrumentation is automatic. It will download the `controller-runtime` and `client-go` libraries required by the controller, instrument the libraries and modify the `go.mod` file of the controller to point to the instrumented libraries. The instrumented libraries are stored in the `sieve-dependency/` folder. To make sure the controller can be successfully built, please copy the Dockerfile used for building the controller image to the `examples/your-controller/build/Dockerfile` and modify the Dockerfile, typically by adding `COPY sieve-dependency/ sieve-dependency/`. As an example, see the [`Dockerfile`](../examples/zookeeper-operator/build/Dockerfile#L17) we prepared for the zookeeper-operator.

Besides, the user also needs to fill the `examples/your-controller/build/build.sh` with the commands to build the controller images. The script is supposed to be run by Sieve in the controller project directory to build the image with the modified Dockerfile. As an example, please refer to the [`build.sh`](../examples/zookeeper-operator/build/build.sh) we prepared for the zookeeper-operator.

After that, please specify following entries in `examples/your-controller/config.json`:
- `github_link`: the link to git clone the controller project
- `commit`: the commit to build and test
- `kubernetes_version`: the version of Kubernetes to test the controller with (e.g., v1.23.1)
- `controller_runtime_version`: the version of the `controller-runtime` used by the controller
- `client_go_version`: the version of the `client-go` used by the controller
- `dockerfile_path`: the relative path from the cloned controller project to the Dockerfile in the project
- `controller_image_name`: the name of the image built by `examples/your-controller/build/build.sh` (e.g., your-controller/latest)

Now run `python3 build.py -p your-controller -m learn`. This command will do the following:
1. download the controller project to `app/your-controller`
2. download and instrument the `controller-runtime` and `client-go` libraries used by the controller
3. copy the instrumented libraries to `app/your-controller/sieve-dependency`
4. modify the `app/your-controller/go.mod` to add the instrumented libraries as dependency
5. copy the (modified) Dockerfile provided by the user to `dockerfile_path` inside `app/your-controller`
6. copy the `build.sh` provided by the user to `app/your-controller`
7. run the `build.sh` to build the image


### Deploy
The second step is to make Sieve able to deploy the controller in a kind cluster.

The user needs to copy the necessary files (e.g., YAML files for installing the controller deployment, CRDs and other resources) to `examples/your-controller/deploy`. The user also needs to modify the controller deployment by doing the following:
1. Add a label: `sievetag: your-controller`. So sieve can find the pod during testing. See [this example](../examples/zookeeper-operator/deploy/default_ns/operator.yaml#L10).
2. Set the controller image repo name to `${SIEVE-DR}`, and set the image tag to `${SIEVE-DT}`. So sieve can switch to different images when testing different bug patterns. See [this example](../examples/zookeeper-operator/deploy/default_ns/operator.yaml#L21).
3. Import configmap `sieve-testing-global-config` as Sieve needs to pass some some configurations to the instrumented controller. See [this example](../examples/zookeeper-operator/deploy/default_ns/operator.yaml#L44).
4. Specify env variables `KUBERNETES_SERVICE_HOST` and `KUBERNETES_SERVICE_PORT`. This is used for testing stale-stateing bugs. See [this example](../examples/zookeeper-operator/deploy/default_ns/operator.yaml#L39).
5. Set `imagePullPolicy` to `IfNotPresent` so that the user does not need to push the image to a remote registry. See [this example](../examples/zookeeper-operator/deploy/default_ns/operator.yaml#L27)
6. Set all the namespace to `default` as for now Sieve can only work with the default namespace

After that, please fill the `examples/your-controller/deploy/deploy.sh` with the steps to deploy the controller to a Kubernetes cluster. As an example, please refer to the [`deploy.sh`](../examples/zookeeper-operator/deploy/deploy.sh) we prepared for the zookeeper-operator.

please specify following entries in `examples/your-controller/config.json`:
- `custom_resource_definitions`: the list of the custom resource definitions managed by the controller in lower case
- `controller_pod_label`: the `sievetag` label set to the controller pod
- `controller_deployment_file_path`: the relative path from `sieve` to the YAML file that is modified by the user

### Test
The last step is to prepare the test workloads. The user needs to provide a command for Sieve to run the test workload by filling `test_command` in `examples/your-controller/config.json`. The command should accept an argument to specify which test case to run. As an example, please refer to the [test command](../examples/zookeeper-operator/config.json#L9) we used for the zookeeper-operator which calls a Python script. The Python script implements two test cases.


Now you are all set. To test your controllers, just build the images:
```
python3 build.py -p kind -m all
python3 build.py -p your-controller -m all
```
First run Sieve learning stage
```
python3 sieve.py -p your-controller -t your-test-case-name -s learn -m learn-twice
```
Sieve will generate the test plans for intermediate-states, unobserved-states and stale-stateing testing patterns in `log/your-controller/your-test-case-name/learn/learn-twice/{intermediate-state, unobserved-states, stale-state}`.
If you want to run one of the test plans:
```
python3 sieve.py -p your-controller -t your-test-case-name -s test -m intermediate-state -c path-to-the-test-plan
```
Sieve will report any bugs it find after the test case is finished.

