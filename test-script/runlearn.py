import sys
sys.path.append('../')

import workloads
import argparse
import os

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automate learning run.")
    parser.add_argument('-d', dest='docker', help="Docker account", default='ghcr.io/sieve-project/action')
    parser.add_argument('-p', dest='operators', help="Operators to test", nargs='+')
    args = parser.parse_args()

    if args.operators is None:
        print('No operator specified, running learning mode for all operators')
        operators = workloads.workloads.keys()
    else:
        operators = args.operators

    for operator in operators:
        for testcase in workloads.workloads[operator]:
            os.system('python3 sieve.py -s learn -p {} -t {} -d {}'.format(operator, testcase, 'ghcr.io/sieve-project/action'))