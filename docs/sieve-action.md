# Using GitHub Actions to run Sieve

Sieve provides a [reusable workflow](https://github.com/sieve-project/sieve/blob/main/.github/workflows/run-sieve.yml)
to make it easy to use Sieve to test a controller with GitHub actions. This lets
developers test out Sieve without having to set up a local environment and also
integrate testing with Sieve into their CI/CD pipeline.

Testing a controller with Sieve requires the test files laid out as described in
the [porting guide](https://github.com/sieve-project/sieve/blob/main/docs/port.md).
The workflow assumes that these files are available in order to test a controller.
The workflow can run both on Ubuntu and MacOS runners. 

## Inputs
The workflow takes the following arguments as inputs:
1. `platform-os` &emsp;&emsp; (optional, default is `ubuntu-latest`)  
   Defines the runner platform to be used for the workflow

2. `controller-name` &nbsp;(required)  
   Name of the controller being tested. E.g. `rabbitmq-operator`

3. `github-repo` &emsp;&emsp; (required)  
   URL of the GitHub repository containing the test files (refer [porting guide](https://github.com/sieve-project/sieve/blob/main/docs/port.md))

4. `github-ref` &emsp; &emsp; &nbsp;(optional)  
   The branch, tag or SHA to checkout. Defaults to the SHA or reference to the event triggering the workflow.

5. `subdirectory` &emsp; &ensp;(optional)  
   The sub-directory in the GitHub repository containing the test files.

6. `workload_name` &emsp; (required)  
   The test workload name that Sieve should use for testing the controller.

The workflow also requires the following two secrets passed as input:
1. `DOCKER_USER` &emsp;&emsp; (required)
2. `DOCKER_TOKEN` &emsp;&ensp; (required)

This is used to log in to the Docker Hub.

## Description

The workflow uses the provided input to run Sieve to test the controller. It
performs the following actions:
 1. Build the controller with Sieve instrumentation in `learn` mode
 2. Run the controller in `learn` mode with the provided test workload so that
    Sieve can generate test plans.
 3. Build the controller with Sieve instrumentation in `test` mode
 4. Run the controller in `test` mode with the provided test workload and
    injected perturbations to identify any bugs in the controller.

Once the workflow completes running, any bugs identified by Sieve will be
logged under the step "Run sieve in test mode".

## Example

An example invocation of the workflow is below:
```yml
name: 'Test Sieve GitHub action on Linux'

on:
  workflow_dispatch:

jobs:
  run-sieve:
    uses: sieve-project/sieve/.github/workflows/run-sieve.yml@main
    with:
      platform-os: ubuntu-latest
      controller-name: kapp-controller
      github-repo: https://github.com/jerrinsg/sieve-action-test.git
      github-ref: main
      subdirectory: kapp-controller-simple
      workload_name: create
    secrets:
      DOCKER_USER: ${{ secrets.DOCKER_USER }}
      DOCKER_TOKEN: ${{ secrets.DOCKER_TOKEN }}
```