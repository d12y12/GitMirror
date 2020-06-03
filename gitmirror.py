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

def print_cmd_result(success=True):
    if success:
        print("Success")
    else:
        print("Failed")
        print("Please check log")

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
        print("Available Service: {}".format(services))
        print("Potential Service: {}".format(services_possible))
        return True
    if options.parse:
        if len(args) != 1:
            usage_error("--parse only take 1 argument <service name>")
            return False
        service_name = args[0]
        print_cmd_result(repo_manager.parse_service(service_name))
        return True
    if options.mirror:
        if len(args) != 1:
            usage_error("--mirror only take 1 argument <service name>")
            return False
        service_name = args[0]
        print_cmd_result(repo_manager.mirror_service(service_name))
        return True
    if options.get:
        if options.get not in ['configs', 'repos']:
            usage_error("--get options should be choice of [configs, repos]")
            return False
        if len(args) not in (1, 2):
            usage_error("--get can take 2 argument <service name> [output file]")
            return False
        service_name = args[0]
        output = ''
        if len(args) == 2:
            output = args[1]
        if options.get == 'configs':
            print_cmd_result(repo_manager.get_service_config(service_name, output))
        if options.get == 'repos':
            print_cmd_result(repo_manager.get_service_repos(service_name, output))
        return True
    if options.add:
        if len(args) != 1:
            usage_error("--add only take 1 argument <service name>")
            return False
        service_name = args[0]
        print_cmd_result(repo_manager.add_service(service_name))
        return True
    if options.remove:
        if len(args) != 1:
            usage_error("--remove only take 1 argument <service name>")
            return False
        service_name = args[0]
        print_cmd_result(repo_manager.remove_service(service_name))
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
        repo_manager.batchrun_service(service_name)
        return True
    if options.init:
        if len(args) > 0:
            usage_error("--init take no argument")
            return False
        repo_manager.init()
        return True

def cli(argv=None):
    print_cmd_header()
    if argv is None:
        argv = sys.argv

    usage = "usage: %prog [options] [service name] [output]"
    parser = optparse.OptionParser(formatter=optparse.TitledHelpFormatter(),
                                   conflict_handler='resolve', usage=usage)
    group_global = optparse.OptionGroup(parser, "Global Options")
    group_global.add_option("--logfile", metavar="FILE",
                     help="log file. if omitted stderr will be used")
    group_global.add_option("--loglevel", metavar="LEVEL", default=None,
                     help="log level (default: DEBUG)")
    group_global.add_option("--nolog", action="store_true",
                     help="disable logging completely")
    parser.add_option_group(group_global)

    parser.add_option("--list", action='store_true', dest='list',
                      help="List all services names available")
    parser.add_option("--parse", action='store_true', dest="parse",
                      help="Parse repositories for <service name>")
    parser.add_option("--mirror", action='store_true', dest="mirror",
                      help="Update from remote & Push to target for <service name>")
    parser.add_option("--get", metavar="CONTENT", dest="get",
                      help="Get content(configs/repos) from <service name> save to [output]")
    parser.add_option("--add", action='store_true', dest="add",
                      help="Create or Update <service name>")
    parser.add_option("--remove", action='store_true', dest="remove",
                      help="Backup and Remove <service name>")

    group_devspace = optparse.OptionGroup(parser, "Devspace Options")    
    group_devspace.add_option("--autoconf", action='store_true', dest="autoconf",
                      help="Auto add service avaialbe and update crontab")
    group_devspace.add_option("--batchrun", action='store_true', dest="batchrun",
                      help="Run parse and mirror for <service name>")
    group_devspace.add_option("--init", action='store_true', dest="init",
                      help="For devspace init all service and first checkout")
    parser.add_option_group(group_devspace)

    if len(argv) == 1:
        parser.print_help()
    else:
        options, args = parser.parse_args(args=argv[1:])
        process(options, args)


if __name__ == '__main__':
    cli()
