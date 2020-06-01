#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import optparse
from repository.utils import get_version, set_logger
from repository import RepositoryManager
from repository.minisetting import Setting


def print_cmd_header():
    print('GitMirror {}'.format(get_version()))


def usage_error(error: str):
    print("Usage Error: {} {}".format(os.path.basename(__file__), error))
    print("Try {} -h for more information".format(os.path.basename(__file__)))


def process(options, args):

    setting = Setting()

    if options.logfile:
        set_logger(setting, log_enable=True, log_file=options.logfile)

    if options.loglevel:
        set_logger(setting, log_enable=True, log_level=options.loglevel)

    if options.nolog:
        set_logger(setting, log_enable=False)

    repo_manager = RepositoryManager(setting)

    if options.list:
        if len(args) > 0:
            usage_error("--list take no argument")
            return False
        services, services_possible = repo_manager.get_services_list()
        print("Service available: {}".format(services))
        print("Possible service available: {}".format(services_possible))
        return True
    if options.parse:
        if len(args) != 1:
            usage_error("--parse only take 1 argument <service name>")
            return False
        service_name = args[0]
        print("parsing <{}> begin...".format(service_name))
        print(repo_manager.parse_service(service_name))
        return True
    if options.mirror:
        if len(args) != 1:
            usage_error("--mirror only take 1 argument <service name>")
            return False
        service_name = args[0]
        print("mirror <{}> begin ...".format(service_name))
        print(repo_manager.mirror_service(service_name))
        return True
    if options.get:
        if options.get not in ['configs', 'repos']:
            usage_error("--get options should be choice of [configs, repos]")
            return False
        if len(args) != 1:
            usage_error("--get only take 1 argument <service name>")
            return False
        service_name = args[0]
        if options.get == 'configs':
            print("get <{}> configuration...".format(service_name))
            print(repo_manager.get_service_config(service_name))
        if options.get == 'repos':
            print("get <{}> repositories...".format(service_name))
            print(repo_manager.get_service_repos(service_name))
        return True
    if options.add:
        if len(args) != 1:
            usage_error("--add only take 1 argument <service name>")
            return False
        service_name = args[0]
        print("add service <{}> ...".format(service_name))
        print(repo_manager.add_service(service_name))
        return True
    if options.remove:
        if len(args) != 1:
            usage_error("--remove only take 1 argument <service name>")
            return False
        service_name = args[0]
        print("remove service <{}> ...".format(service_name))
        print(repo_manager.remove_service(service_name))
        return True
    if options.autoconf:
        if len(args) > 0:
            usage_error("--autoconf take no argument")
            return False
        repo_manager.autoconf()
        return True
    if options.batchrun:
        if len(args) != 1:
            usage_error("--batchrun only take 1 argument <service name>")
            return False
        service_name = args[0]
        print("batchrun service <{}> ...".format(service_name))
        print(repo_manager.batchrun_service(service_name))
        return True

def cli(argv=None):
    print_cmd_header()
    if argv is None:
        argv = sys.argv
    usage = "usage: %prog [options] [service name]"
    parser = optparse.OptionParser(formatter=optparse.TitledHelpFormatter(),
                                   conflict_handler='resolve', usage=usage)
    group = optparse.OptionGroup(parser, "Global Options")
    group.add_option("--logfile", metavar="FILE",
                     help="log file. if omitted stderr will be used")
    group.add_option("-L", "--loglevel", metavar="LEVEL", default=None,
                     help="log level (default: debug)")
    group.add_option("--nolog", action="store_true",
                     help="disable logging completely")
    parser.add_option_group(group)

    parser.add_option("--list", action='store_true', dest='list',
                      help="List all services names available")
    parser.add_option("--parse", action='store_true', dest="parse",
                      help="Parse repositories for <service name>")
    parser.add_option("--mirror", action='store_true', dest="mirror",
                      help="Update from remote & Push to target for <service name>")
    parser.add_option("--get", metavar="configs or repos", dest="get",
                      help="Get configuration or repositories for <service name>")
    parser.add_option("--add", action='store_true', dest="add",
                      help="Create or Update <service name>")
    parser.add_option("--remove", action='store_true', dest="remove",
                      help="Backup and Remove <service name>")
    parser.add_option("--autoconf", action='store_true', dest="autoconf",
                      help="Auto add service avaialbe and update crontab")
    parser.add_option("--batchrun", action='store_true', dest="batchrun",
                      help="Run parse and mirror for <service name>")

    if len(argv) == 1:
        parser.print_help()
    else:
        options, args = parser.parse_args(args=argv[1:])
        process(options, args)


if __name__ == '__main__':
    cli()
