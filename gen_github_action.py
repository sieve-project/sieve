from reprod import reprod_map
import yaml
import os
from common import sieve_modes

jobs = {}

for operator in reprod_map:
    job = {
        'runs-on': 'ubuntu-latest',
        'env': {'GOPATH': '/home/runner/go',
        'KUBECONFIG': '/home/runner/.kube/config'},
        'steps': [
            {'uses': 'actions/checkout@v2'},
            {'name': 'Setup Git',
             'run': 'git config --global user.name "sieve"\ngit config --global user.email "sieve@sieve.com"'},
            {'name': 'Setup Go environment',
             'uses': 'actions/setup-go@v2.1.3',
             'with': {'go-version': 1.15}},
            {'name': 'Setup Python',
             'uses': 'actions/setup-python@v2.2.2',
             'with': {'python-version': 3.7}},
            {'name': 'Setup GitHub Package Registry',
             'run': 'echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u "${{ github.actor }}" --password-stdin'},
            {'name': 'Install Python Packages',
             'run': 'pip install -r requirements.txt'},
            {'name': 'Install Kind', 'run': 'go get sigs.k8s.io/kind\nkind'},
            {'name': 'Install Mage',
             'run': 'go get -u github.com/magefile/mage\nmage -h'},
            {'name': 'Install Helm',
             'run': 'wget https://get.helm.sh/helm-v3.6.0-linux-amd64.tar.gz\ntar -zxvf helm-v3.6.0-linux-amd64.tar.gz\nsudo mv linux-amd64/helm /usr/local/bin/helm\nhelm'},
        ]
    }
    build_image = {'name': 'Build Image', 'run': ''}
    collect_resources = {'uses': 'actions/upload-artifact@v2',
        'with': {'name': 'sieve-%s-data'%(operator), 'path': 'data/%s'%(operator)}}
    collect_log = {'uses': 'actions/upload-artifact@v2',
        'with': {'name': 'sieve-%s-log'%(operator), 'path': 'log'}}

    build_modes = {
        "learn": True,
        sieve_modes.TIME_TRAVEL: False,
        sieve_modes.OBS_GAP: False,
        sieve_modes.ATOM_VIO: False
    }
    workload_set = set()
    
    for bug in reprod_map[operator]:
        workload = reprod_map[operator][bug][0]
        config_name = reprod_map[operator][bug][1]
        config = yaml.safe_load(open(os.path.join("reprod", config_name)).read())
        build_modes[config['mode']] = True
        workload_set.add(workload)
#         print(operator, bug, workload, config['mode'])
    
    build_image_run = []
    for mode in build_modes:
        if build_modes[mode]:
            build_image_run.append('python3 build.py -p %s -m %s -d $IMAGE_NAMESPACE'%(operator, mode))

    build_image['run'] = '\n'.join(build_image_run)
    sieve_learn = [{'name': 'Sieve Learn: %s %s'%(operator, workload), 'run': 'python3 sieve.py -p %s -t %s -s learn -m learn-twice -d $IMAGE_NAMESPACE'%(operator, workload)} for workload in workload_set]
    sieve_test = [{'name': 'Sieve Test: %s %s'%(operator, bug), 'run': 'python3 reprod.py -p %s -b %s -d $IMAGE_NAMESPACE'%(operator, bug)} for bug in reprod_map[operator].keys()]
    job['steps'].append(build_image)
    job['steps'].extend(sieve_learn)
    job['steps'].append(collect_resources)
    job['steps'].extend(sieve_test)
    job['steps'].append(collect_log)
    jobs[operator] = job

config = {
    'name': 'Sieve Test',
    'on': {
        'pull_request': None,
        'workflow_dispatch': None,
        'schedule': [{'cron': '0 4 * * *'}]},
    'env': {'IMAGE_NAMESPACE': 'ghcr.io/sieve-project/action'},
    'jobs': jobs,
}

# dump
config_path = ".github/workflows/sieve-test.yml"
open(config_path, "w").write("# The file is automatically generated based on reprod.py\n"+yaml.dump(config, default_flow_style=False, sort_keys=False))
print("CI config generated to %s"%(config_path))