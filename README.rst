:orphan:

GitMirror
==================

目的
-------

* git 本地镜像工具

命令
-------

Usage
=====
  gitmirror.py [options] [service name] [output]

Options
=======
--help, -h              show this help message and exit
--list                  List all services names available
--parse                 Parse repositories for <service name>
--mirror                Update from remote & Push to target for <service name>
--get=CONTENT           Get content(configs/repos)for <service name> save to [output]
--add                   Create or Update <service name>
--remove                Backup and Remove <service name>

Global Options
--------------
--logfile=FILE          log file. if omitted stderr will be used
--loglevel=LEVEL        log level (default: debug)
--nolog                 disable logging completely

Devspace Options
----------------
--autoconf              Auto add service avaialbe and update crontab
--batchrun              Run parse and mirror for <service name>
--init                  For devspace init all service and first checkout
