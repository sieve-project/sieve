import os
import controllers
import optparse

if __name__ == "__main__":
    usage = "usage: python3 run.py [options]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("-p", "--project", dest="project",
                      help="specify PROJECT to build: cassandra-operator or zookeeper-operator", metavar="PROJECT", default="cassandra-operator")
    parser.add_option("-m", "--mode", dest="mode",
                      help="build MODE: learn, time-travel, sparse-read", metavar="MODE", default="learn")
    parser.add_option("-s", "--sha", dest="sha",
                      help="SHA of the project", metavar="SHA", default="none")
    (options, args) = parser.parse_args()

    project = options.project
    mode = options.mode
    sha = options.sha if options.sha != "none" else controllers.sha[project]
    crv = controllers.controller_runtime_version[project]
    cgv = controllers.client_go_version[project]
    link = controllers.github_link[project]
    df = controllers.docker_file[project]

    os.system("CRV=%s CGV=%s GL=%s DF=%s ./build.sh -p %s -m %s -s %s " %
              (crv, cgv, link, df, project, mode, sha))
