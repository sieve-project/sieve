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
    parser.add_option("-d", "--docker", dest="docker",
                      help="DOCKER repo that you have access", metavar="DOCKER", default="none")
    (options, args) = parser.parse_args()

    dr = options.docker if options.docker != "none" else controllers.docker_repo
    if options.project == "kubernetes":
        os.system("DR=%s ./build.sh -p %s -m %s" %
                  (dr, options.project, options.mode))
    else:
        sha = options.sha if options.sha != "none" else controllers.sha[options.project]
        crv = controllers.controller_runtime_version[options.project]
        cgv = controllers.client_go_version[options.project]
        link = controllers.github_link[options.project]
        df = controllers.docker_file[options.project]
        os.system("CRV=%s CGV=%s GL=%s DF=%s DR=%s ./build.sh -p %s -m %s -s %s " %
                  (crv, cgv, link, df, dr, options.project, options.mode, sha))
