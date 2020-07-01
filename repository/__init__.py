#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from os.path import join, abspath, dirname, exists, isfile, splitext, basename
from shutil import move
import datetime
import filecmp
import subprocess
import logging
import platform
from .minisetting import Setting
from .store import RepositoryStore
from .parser import Cgit, GitHub, Gitee, ParserError
from .mirror import RepositoryMirror
from .utils import config_logging

# logger = logging.getLogger('RepositoryManager')

class RepositoryManager:
    def __init__(self, setting: Setting = None):
        self.setting = Setting() if not setting else setting
        config_logging(self.setting)
        self.store = RepositoryStore(setting)
        self.parsers = {
            'cgit': Cgit(setting),
            'github': GitHub(setting),
            'gitee': Gitee(setting)
        }
        self.mirror = RepositoryMirror(setting)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def git_timeout_config(self):
        speed = self.setting['GIT_LOW_SPEED'] if self.setting['GIT_LOW_SPEED'] else 1000
        timeout = self.setting['GIT_LOW_TIMEOUT'] if self.setting['GIT_LOW_TIMEOUT'] else 60
        ret = subprocess.run(["git", "config", "--global", "http.lowSpeedLimit", str(speed)], stdout=subprocess.DEVNULL)
        ret = subprocess.run(["git", "config", "--global", "http.lowSpeedTime", str(timeout)], stdout=subprocess.DEVNULL)

    def get_services_list(self):
        services = []
        services_possible = []
        if exists(self.setting['DATABASE_DIR']):
            for file in os.listdir(self.setting['DATABASE_DIR']):
                file_path = join(self.setting['DATABASE_DIR'], file)
                if isfile(file_path):
                    file_name, file_extension = splitext(basename(file_path))
                    if file_extension == '.db':
                        services.append(file_name)
                    if file_extension == '.sql':
                        services_possible.append(file_name)   
        else:
            self.logger.error("Database directory not exists!")
        return services, services_possible

    def service_name_available(self, service_name: str):
        services, services_possible = self.get_services_list()
        if service_name not in services:
            self.logger.error('<{}.db> not found'.format(service_name))
            return False
        else:
            return True
    
    def _get_sqlite_file(self, service_name: str):
        return join(self.setting['DATABASE_DIR'], service_name + '.db')
    
    def _get_sql_file(self, service_name: str):
        return join(self.setting['DATABASE_DIR'], service_name + '.sql')
    
    def backup_database(self, service_name: str):
        sqlite_file = self._get_sqlite_file(service_name)
        try:
            backup_sql_name = self.store.get_original_sql(sqlite_file)
        except Exception as e:
            self.logger.error('db failed: {}'.format(str(e)))
            return False
        str_time = ('_' + '_'.join(backup_sql_name.split('_')[1:3])).split('.')[0]
        backup_sqlite_file = join(self.setting['DB_BACKUP_DIR'], service_name + str_time + '.db')
        move(sqlite_file, backup_sqlite_file)
        return True
    
    def backup_sql_file(self, service_name: str):
        sqlite_file = self._get_sqlite_file(service_name)
        sql_file = self._get_sql_file(service_name)
        backup_dir = self.setting['DB_BACKUP_DIR']
        os.makedirs(backup_dir, exist_ok=True)
        dst_file = join(backup_dir, service_name +
                        datetime.datetime.now().strftime("_%Y%m%d_%H%M%S") + '.sql')
        try:
            self.store.update_original_sql(sqlite_file, basename(dst_file))
            move(sql_file, dst_file)
        except Exception as e:
            if exists(sqlite_file):
                os.remove(sqlite_file)
                self.logger.error('failed: {}'.format(str(e)))
            return False
        return True

    def remove_service(self, service_name: str):
        self.logger.info("remove service <{}>".format(service_name))
        if not self.service_name_available(service_name):
            return False
        if self.backup_database(service_name):
            self.logger.info("remove service <{}> success".format(service_name))
            return True
        else:
            self.logger.error("remove service <{}> failed".format(service_name))
            return False

    def update_service(self, service_name: str):
        self.logger.info("update service <{}>".format(service_name))
        backup_dir = join(self.setting['BACKUP_DIR'], 'database')
        if not exists(backup_dir):
            self.logger.error("update service <{}> failed: cant find backup, manual backup database and " \
                   "use add function to recreate service".format(service_name))
        sqlite_file = self._get_sqlite_file(service_name)
        sql_file = self._get_sql_file(service_name)
        try:
            backup_sql_name = self.store.get_original_sql(sqlite_file)
        except Exception as e:
            self.logger.error('db failed: {}'.format(str(e)))
            return False
        backup_sql_file = join(backup_dir, backup_sql_name)
        if filecmp.cmp(sql_file, backup_sql_file):
            os.remove(sql_file)
            self.logger.info("update service <{}> no need: same sql file".format(service_name))
            return True
        else:
            if not self.backup_database(service_name):
                self.logger.error("backup service <{}> failed".format(service_name))
                return False
            self.logger.info("backup service <{}> success, now add it again".format(service_name))
            return self.add_service(service_name)

    def add_service(self, service_name: str):
        self.logger.info("add service <{}>".format(service_name))
        services, services_possible = self.get_services_list()
        # not sql file in database dir
        if service_name not in services_possible:
            self.logger.error('failed: {}.sql not found'.format(service_name))
            return 
        # sql file exist, database also exist, should use update
        if service_name in services:
            return self.update_service(service_name)
        # sql file exist, database not exist, create database
        sqlite_file = self._get_sqlite_file(service_name)
        sql_file = self._get_sql_file(service_name)
        try:
            self.store.create(sql_file, sqlite_file)
        except Exception as e:
            if exists(sqlite_file):
                os.remove(sqlite_file)
            self.logger.error('db failed: {}'.format(str(e)))
            return False
        if self.backup_sql_file(service_name):
            self.logger.info("add service <{}> success".format(service_name))
            return True
        else:
            self.logger.error("add service <{}> failed".format(service_name))
            return False

    def parse_service(self, service_name: str):
        self.logger.info("parse service <{}>".format(service_name))
        repo_list = []
        if not self.service_name_available(service_name):
            return False
        sqlite_file = self._get_sqlite_file(service_name)
        status_path = self.setting['LOG_DIR']
        if not exists(status_path):
            os.mkdir(status_path)
        try:
            repositories = self.store.get_repositories(sqlite_file)
        except Exception as e:
            self.logger.error('failed: {}'.format(str(e)))
            return False
        if repositories:
            repositories = json.loads(repositories)
            for repositories_type, repositories_sources in repositories.items():
                if repositories_type in self.parsers:
                    if repositories_sources:
                            for repo in self.parsers[repositories_type].parse(repositories_sources, sqlite_file,
                                                                              status_path):
                                repo_list.append(repo)
                else:
                    self.logger.error("failed: Unsupport parser type: {}".format(repositories_type))
                    return False
        else:
            self.logger.info("failed: Empty repository source: {}".format(sqlite_file))
            return False
        return repo_list if repo_list else False

    def _get_cgit_url(self, service_name='', schema=''):
        cgit_url = ''
        sqlite_file = self._get_sqlite_file(service_name)
        try:
            host = self.store.get_host(sqlite_file)
        except Exception as e:
            self.logger.error('failed: {}'.format(str(e)))
            return cgit_url
        schema = schema if schema else 'http'
        cgit_url = host if host.startswith('http') else schema+'://{}'.format(host)
        cgit_url = cgit_url if cgit_url.endswith('/') else cgit_url + '/'
        cgit_url = cgit_url + service_name
        return cgit_url

    def mirror_service(self, service_name: str):
        self.logger.info("mirror service <{}>".format(service_name))
        if not self.service_name_available(service_name):
            return False
        sqlite_file = self._get_sqlite_file(service_name)
        status_path = self.setting['LOG_DIR']
        os.makedirs(status_path, exist_ok=True)
        data_dir = join(self.setting['DATA_DIR'], service_name)
        os.makedirs(data_dir, exist_ok=True)
        cgitrc_file = join(self.setting['DATA_DIR'], service_name, service_name+'.repo')
        cgit_url = self._get_cgit_url(service_name)
        if not cgit_url:
            return False
        self.git_timeout_config()
        self.mirror.sync(data_dir=data_dir, database=sqlite_file, status_path=status_path)
        self.logger.info("generate cgitrc for service <{}>".format(service_name))
        self.mirror.generate_cgitrc(data_dir=data_dir, database=sqlite_file,
                                     cgit_url=cgit_url, cgitrc_file=cgitrc_file)
        return True

    def get_service_config(self, service_name: str, output=''):
        self.logger.info("get service <{}> configuration".format(service_name))
        if not self.service_name_available(service_name):
            return False
        sqlite_file = self._get_sqlite_file(service_name)
        try:
            config = self.store.get_full_config(sqlite_file)
        except Exception as e:
            self.logger.error('failed: {}'.format(str(e)))
            return False
        config['repositories'] = json.loads(config['repositories'])
        if output:
            with open(output, 'w', encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        else:
            print(json.dumps(config, indent=2))
        return True

    def get_service_repos(self, service_name: str, output=''):
        self.logger.info("get service <{}> repositories".format(service_name))
        if not self.service_name_available(service_name):
            return False
        sqlite_file = self._get_sqlite_file(service_name)
        try:
            repos = self.store.get_repository_list(sqlite_file)
        except Exception as e:
            self.logger.error('failed: {}'.format(str(e)))
            return False
        if output:
            with open(output, 'w', encoding="utf-8") as f:
                json.dump(repos, f, indent=2, ensure_ascii=False)
        else:
            print(json.dumps(repos, indent=2))
        return True

    def set_crontab(self):
        if platform.system() != 'Linux':
            self.logger.warning("Not Linux system, Crontab will not set!")
        user = subprocess.run(["whoami"], stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
        if user == 'root':
            self.logger.warning("you are using root user")
            print("set crontab for root user")
        self.logger.info("set crontab for user {}".format(user))
        cron_header = 'SHELL=/bin/sh\n' \
                      'PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin\n\n' \
                      '# m h dom mon dow user  command\n'
        services, services_possible = self.get_services_list()
        crontab = []
        for service_name in services:
            sqlite_file = self._get_sqlite_file(service_name)
            try:
                cron = self.store.get_crontab(sqlite_file)
            except Exception as e:
                self.logger.error('failed: {}'.format(str(e)))
                return False
            if cron:
                app = self.setting['CMD']
                cron_log = join(self.setting['LOG_DIR'], service_name+'.log')
                crontab.append('{} {} {} {} >> {} 2>&1\n'.format(cron, app, '--batchrun', service_name, cron_log))
        cron_path = self.setting['CRON_FILE']
        if crontab:
            cron = cron_header + "".join(crontab)
            with open(cron_path, "w") as f:
                f.write(cron)
            # "crontab -u user cron_path" need root in alpine
            if platform.system() == 'Linux':
                self.logger.info("set cron tab")
                subprocess.run(['crontab', cron_path])
            # "crond reload" not exists in alpine
            # self.logger.info("reload cron config")
            # subprocess.run(['/etc/init.d/cron', 'reload'])
        else:
            self.logger.info("No cron job found!")
        return True

    def autoconf(self):
        services, services_possible = self.get_services_list()
        for service_name in services_possible:
            self.add_service(service_name)
        self.set_crontab()

    def batchrun_service(self, service_name:str):
        self.parse_service(service_name)
        self.mirror_service(service_name)
    
    def init(self):
        services, services_possible = self.get_services_list()
        for service_name in services_possible:
            self.add_service(service_name)
        services, services_possible = self.get_services_list()
        for service_name in services:
            self.batchrun_service(service_name)
