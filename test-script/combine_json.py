import glob
import json
import time
import os

def merge(result, patch):
    '''
    Recursive function to merge two dict
    '''
    for key in patch:
        if key not in result:
            result[key] = patch[key]
        else:
            if type(patch[key]) is not dict:
                print('ERROR: Duplicate config, overwriting')
                result[key] = patch[key]
            else:
                merge(result[key], patch[key])

if __name__ == '__main__':
    t = time.localtime()
    json_names = glob.glob('../sieve_test_results/*.json')

    result = {}
    result['failed'] = []
    for fname in json_names:
        with open(fname, 'r') as in_json:
            patch = json.load(in_json)
            merge(result, patch)

    with open('commands.txt', 'r') as command_file:
        commands = command_file.read().splitlines()
        for command in commands:
            args = command.split()
            result_name = '%s-%s-%s' % (args[5], args[9], os.path.splitext(os.path.basename(args[11]))[0])
            if not any(result_name in s for s in json_names):
                print(result_name)
                result['failed'].append(command)

    with open('test-summary-{}-{}-{}-{}-{}.json'.format(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min), 'w') as merged:
        json.dump(result, merged, indent=4, sort_keys=True)
