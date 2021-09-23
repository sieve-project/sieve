import glob
import json
import time

if __name__ == '__main__':
    t = time.localtime()
    json_names = glob.glob('../sieve_test_results/*.json')

    result = {}
    for fname in json_names:
        with open(fname, 'r') as in_json:
            result[fname] = json.load(in_json)

    with open('test-summary-{}-{}-{}-{}-{}.json' % (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min), 'w') as merged:
        json.dump(result, merged, indent=4)
