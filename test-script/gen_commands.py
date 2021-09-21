import glob
import os
import argparse

modes = ['atomicity-violation', 'observability-gap', 'time-travel']
mode_map = {
    'atomicity-violation': 'atom-vio',
    'observability-gap': 'obs-gap',
    'time-travel': 'time-travel'
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate testcase commands into a file.")
    parser.add_argument('-d', dest='docker', help="Docker account", default='ghcr.io/sieve-project/action')
    parser.add_argument('-o', dest='output', help="Output file name", default='commands.txt')
    args = parser.parse_args()

    with open(args.output, 'w') as command_file, open('pull-commands.txt', 'w') as pull_command_file:
        # pull all k8s images
        pull_command_file.write('docker pull {}/node:{}\n'.format(args.docker, 'learn'))
        pull_command_file.write('docker pull {}/node:{}\n'.format(args.docker, 'time-travel'))
        pull_command_file.write('docker pull {}/node:{}\n'.format(args.docker, 'observability-gap'))
        pull_command_file.write('docker pull {}/node:{}\n'.format(args.docker, 'atomicity-violation'))

        for operator in os.listdir('../log'):
            for mode in modes:
                # for each operator X mode, pull the corresponding image
                pull_command_file.write('docker pull {}/{}:{}\n'.format(args.docker, operator, mode))

                # write commands for each test case
                for testcase in os.listdir(os.path.join('../log', operator)):
                    configs = glob.glob(os.path.join(os.path.abspath('../log'), operator, testcase, 'learn/learn-once', mode, '*.yaml'))
                    for config in configs:
                        command_file.write('python3 sieve.py -s test -p {} -m {} -t {} -c {} -d {}\n'.format(operator, mode_map[mode], testcase, config, args.docker))
