import glob
import json

if __name__ == '__main__':
    json_names = glob.glob('../sieve_test_results/*.json')

    result = {}
    for fname in json_names:
        with open(fname, 'r') as in_json:
            result[fname] = json.load(in_json)

    with open('merged.json', 'w') as merged:
        json.dump(result, merged, indent=4)
