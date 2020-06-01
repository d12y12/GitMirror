#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from os.path import join, abspath, dirname, exists, isfile, splitext, basename
from shutil import move
import datetime
import filecmp
import subprocess
from .minisetting import Setting
from .store import RepositoryStore
from .parser import Cgit, GitHub, ParserError
from .mirror import RepositoryMirror

class RepositoryManager:
    def __init__(self, setting: Setting = None):
        self.setting = Setting() if not setting else setting
        self.store = RepositoryStore(setting)
        self.parsers = {
            'cgit': Cgit(setting),
            'github': GitHub(setting)
        }
        self.mirror = RepositoryMirror(setting)
    
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
            return services, services_possible
        else:
            raise ValueError("Database directory not found!")

    def remove_service(self, service_name: str):
        services, services_possible = self.get_services_list()
        if service_name not in services:
            return 'failed: {} not found'.format(service_name)
        backup_dir = join(self.setting['BACKUP_DIR'], 'database')
        if not exists(backup_dir):
            return "failed: cant find backup, manual backup database"
        sqlite_file = join(self.setting['DATABASE_DIR'], service_name + '.db')
        backup_sql_name = self.store.get_original_sql(sqlite_file)
        str_time = ('_' + '_'.join(backup_sql_name.split('_')[1:3])).split('.')[0]
        backup_sqlite_file = join(backup_dir, service_name + str_time + '.db')
        move(sqlite_file, backup_sqlite_file)
        return 'success'

    def update_service(self, service_name: str):
        backup_dir = join(self.setting['BACKUP_DIR'], 'database')
        if not exists(backup_dir):
            return "update service <{}> failed: cant find backup, manual backup database and " \
                   "use add function to recreate service".format(service_name)
        sqlite_file = join(self.setting['DATABASE_DIR'], service_name + '.db')
        sql_file = join(self.setting['DATABASE_DIR'], service_name + '.sql')
        backup_sql_name = self.store.get_original_sql(sqlite_file)
        backup_sql_file = join(backup_dir, backup_sql_name)
        if filecmp.cmp(sql_file, backup_sql_file):
            os.remove(sql_file)
            return "update service <{}> no need: same sql file".format(service_name)
        else:
            str_time =('_' + '_'.join(backup_sql_name.split('_')[1:3])).split('.')[0]
            backup_sqlite_file = join(backup_dir, service_name + str_time + '.db')
            move(sqlite_file, backup_sqlite_file)
            print("back up database success, add service <{}>".format(service_name))
            return self.add_service(service_name)

    def add_service(self, service_name: str):
        services, services_possible = self.get_services_list()
        # not sql file in database dir
        if service_name not in services_possible:
            return 'failed: {}.sql not found'.format(service_name)
        # sql file exist, database also exist, should use update
        if service_name in services:
            return self.update_service(service_name)
        # sql file exist, database not exist, create database
        sqlite_file = join(self.setting['DATABASE_DIR'], service_name + '.db')
        sql_file = join(self.setting['DATABASE_DIR'], service_name + '.sql')
        try:
            self.store.create(sql_file, sqlite_file)
        except Exception as e:
            if exists(sqlite_file):
                os.remove(sqlite_file)
            return 'failed: {}'.format(str(e))
        if not exists(self.setting['BACKUP_DIR']):
            os.mkdir(self.setting['BACKUP_DIR'])
        backup_dir = join(self.setting['BACKUP_DIR'], 'database')
        if not exists(backup_dir):
            os.mkdir(backup_dir)
        dst_file = join(backup_dir, service_name +
                        datetime.datetime.now().strftime("_%Y%m%d_%H%M%S") + '.sql')
        try:
            self.store.update_original_sql(sqlite_file, basename(dst_file))
        except Exception as e:
            if exists(sqlite_file):
                os.remove(sqlite_file)
            return 'failed: {}'.format(str(e))

        move(sql_file, dst_file)
        return 'success'

    def parse_service(self, service_name: str, parse_only=False):
        services, services_possible = self.get_services_list()
        if service_name not in services:
            return 'failed: {}.db not found'.format(service_name)
        sqlite_file = join(self.setting['DATABASE_DIR'], service_name + '.db')
        status_path = self.setting['LOG_DIR']
        if not exists(status_path):
            os.mkdir(status_path)
        try:
            repositories = self.store.get_repositories(sqlite_file)
        except Exception as e:
            return 'failed: {}'.format(str(e))

        if repositories:
            repositories = json.loads(repositories)
            for repositories_type, repositories_sources in repositories.items():
                if repositories_type in self.parsers:
                    if repositories_sources:
                        if parse_only:
                            for repo in self.parsers[repositories_type].parse(repositories_sources):
                                print(repo)
                        else:
                            for repo in self.parsers[repositories_type].parse(repositories_sources, sqlite_file,
                                                                              status_path):
                                print(repo)
                else:
                    return "failed: Unsupport parser type: {}".format(repositories_type)
        else:
            return "failed: Empty repository source: {}".format(sqlite_file)
        return 'finished'

    def mirror_service(self, service_name: str):
        services, services_possible = self.get_services_list()
        if service_name not in services:
            return 'failed: {}.db not found'.format(service_name)
        sqlite_file = join(self.setting['DATABASE_DIR'], service_name + '.db')
        status_path = self.setting['LOG_DIR']
        data_dir = join(self.setting['DATA_DIR'], service_name)
        if not exists(data_dir):
            os.mkdir(data_dir)
        cgitrc_file = join(self.setting['CGITRC_DIR'], service_name+'.repo')
        if not exists(status_path):
            os.mkdir(status_path)
        try:
            host = self.store.get_host(sqlite_file)
        except Exception as e:
            return 'failed: {}'.format(str(e))
        host = host if host.startswith('http') else 'https://{}'.format(host)
        host = host if host.endswith('/') else host + '/'
        host = host + service_name
        self.git_timeout_config()
        self.mirror.sync(data_dir=data_dir, database=sqlite_file, status_path=status_path)
        self.mirror.generate_cgitrc(data_dir=data_dir, database=sqlite_file,
                                     cgit_url=host, cgitrc_file=cgitrc_file)
        return 'finished'

    def get_service_config(self, service_name: str):
        services, services_possible = self.get_services_list()
        if service_name not in services:
            return 'failed: {}.db not found'.format(service_name)
        sqlite_file = join(self.setting['DATABASE_DIR'], service_name + '.db')
        try:
            config = self.store.get_full_config(sqlite_file)
        except Exception as e:
            return 'failed: {}'.format(str(e))
        print(config)
        return 'finished'

    def get_service_repos(self, service_name: str):
        services, services_possible = self.get_services_list()
        if service_name not in services:
            return 'failed: {}.db not found'.format(service_name)
        sqlite_file = join(self.setting['DATABASE_DIR'], service_name + '.db')
        try:
            repos = self.store.get_repository_list(sqlite_file)
        except Exception as e:
            return 'failed: {}'.format(str(e))
        print(repos)
        return 'finished'

    def set_service_cron(self, service_name):
        services, services_possible = self.get_services_list()
        if service_name not in services:
            return 'failed: {}.db not found'.format(service_name)
        sqlite_file = join(self.setting['DATABASE_DIR'], service_name + '.db')
        try:
            crontab = self.store.get_crontab(sqlite_file)
        except Exception as e:
            return 'failed: {}'.format(str(e))
        user = 'root'
        app = self.setting['CMD']
        cron = '{} {} {} {} {}\n'.format(crontab, user, app, '--batchrun', service_name)
        cron_path = join(self.setting['CRON_DIR'], service_name)                                    
        with open(cron_path, "w") as f:
            f.write(cron)
        return 'success'
    
    def autoconf(self):
        services, services_possible = self.get_services_list()
        for service_name in services_possible:
            print("add service <{}>".format(service_name))
            print(self.add_service(service_name))
        services, services_possible = self.get_services_list()
        for service_name in services:
            print("set service <{}> crontab".format(service_name))
            print(self.set_service_cron(service_name))

    def batchrun_service(self, service_name:str):
        self.parse_service(service_name)
        self.mirror_service(service_name)
