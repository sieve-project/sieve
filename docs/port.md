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

Now run `python3 build.py -c your-controller -m learn`. This command will do the following:
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
The last step is to prepare the end-to-end test workloads. The user needs to provide a command for Sieve to run the test workload by filling `test_command` in `examples/your-controller/config.json`. The command should accept an argument to specify which test case to run. As an example, please refer to the [test command](../examples/zookeeper-operator/config.json#L9) we used for the zookeeper-operator which calls a Python script. The Python script implements two test cases.

One common challenge to implement end-to-end test workloads is to know when the cluster becomes stable after each test command. For example, a single `kubectl` command that creates/updates/deletes the custom resource object might trigger a lot of controller actions that create/update//delete secondary objects that are owned by the custom resource object. The best practice is to wait until the cluster is stable before issuing the next command or ending the test workload, since this generates a stable cluster state sequence. Sieve detects bugs by checking cluster state sequence, and unstable sequence can lead to false alarms. Sieve provides APIs (e.g., `wait_for_pod_status`) for users to specify the waiting condition like waiting for certain status (terminated, running) of certain resource (pod, statefulset).

As an example, imagine that if the last command in the workload deletes the custom resource object, which will trigger a series of pod/statefulset deletions. If we do not end the test workload before all the objects are deleted, the end state might or might not contain the pod/statefulset objects depending on how fast Kubernetes GC is so in that particular run. And the inconsistency between the end states could make Sieve report many false alarms.

Of course, if a bug gets triggered and prevents the controller's action forever, it is not a false alarm bug an exciting true alarm. The `wait_for_pod_status` has a default timeout (i.e., 10min) which should be more than enough for most controller actions. If the timeout is reached, Sieve will report it as an alarm.

Now you are all set. To test your controllers, just build the images:
```
python3 build.py -m all
python3 build.py -c your-controller -m all
```
First run Sieve learning stage
```
python3 sieve.py -c your-controller -w your-test-workload-name -m generate-oracle
```
Sieve will generate the test plans for intermediate-states, unobserved-states and stale-states testing patterns in `sieve_learn_results/your-controller/your-test-workload-name/generate-oracle/learn.yaml/{intermediate-state, unobserved-states, stale-state}`.

If you want to run one of the test plans:
```
python3 sieve.py -c your-controller -p path-to-the-test-plan
```
Sieve will report any bugs it find after the test case is finished.

If you want to run all the test plans in a folder:
```
python3 sieve.py -c your-controller -p path-to-the-folder --batch
```
All the test results will appear in `sieve_test_results` as json files.
You can focus on the test results that indicate potential bugs by
```
python3 report_bugs.py
```
and it will report
```
Please refer to the following test results for potential bugs found by Sieve
test-result-1
test-result-2
test-result-3
...
```

Each test result file contains information for debugging:
```
{
    "your-controller": {
        "your-test-workload": {
            "test": {
                "path-to-the-test-plan": {
                    "duration": xxx,
                    "injection_completed": xxx,
                    "workload_completed": xxx,
                    "number_errors": xxx,
                    "detected_errors": xxx,
                    "no_exception": xxx,
                    "exception_message": xxx,
                    "test_config_content": xxx,
                    "host": xxx
                }
            }
        }
    }
}
```
and you might need to look into the controller to figure out the bug.

To help diagnosis, you can reproduce the test failure by
```
python3 sieve.py -c your-controller -p path-to-the-test-plan
```
