#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mirror git repositories from url, maintaining metadata.

This can be useful when maintaining a local mirror.
"""

import os
from os.path import join, exists, isdir, abspath, normpath, basename, dirname
import json
import shutil
import subprocess
import time
import logging
from hashlib import md5

from .minisetting import Setting
from .utils import get_logger
from .store import Repository, RepositoryStore


class MirrorError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class RepositoryMirror:
    def __init__(self, setting: Setting = None):
        self.setting = setting if setting else Setting()
        self.failed_list = []
        self.logger = logging.getLogger(self.__class__.__name__)
        self.mirrored = []

    def get_source_dir_from_url(self, source_url: str):
        return md5(source_url.encode()).hexdigest()

    def get_repository_path(self, data_dir, repository):
        name = repository['name'] if repository['name'].endswith('.git') else repository['name'] + '.git'
        source_path = self.get_source_dir_from_url(repository['source'])
        repository_path = join(source_path, name)
        repository_path = join(data_dir, repository_path)
        repository_path = normpath(abspath(repository_path)).replace('\\', '/')
        return  repository_path

    def mirror(self, data_dir='', repository=None, error_callback=None):
        """
        Mirror a Git repository, maintaining metadata.

        :param repository: information about the repository to mirror
        """
        if not error_callback:
            error_callback = self.process_error
        source_path = join(data_dir, self.get_source_dir_from_url(repository['source']))
        if not exists(source_path):
            os.mkdir(source_path)
        clone_url = repository["clone_url"].split(',')[0]
        repo_dir = self.get_repository_path(data_dir, repository)
        if not isdir(repo_dir):
            self.logger.info("Mirror: {}".format(repository['name']))
            ret = subprocess.run(["git", "clone", "--mirror", clone_url, repo_dir], stdout=subprocess.DEVNULL)
            if ret.returncode != 0:
                error_callback("Mirror Failed: {}".format(repository['name']))
                return False
        else:
            self.logger.info("Update: {}".format(repository['name']))
            ret = subprocess.run(["git", "--git-dir", repo_dir, "remote", "update", "--prune"], stdout=subprocess.DEVNULL)
            if ret.returncode != 0:
                error_callback("Update Failed: {}".format(repository['name']))
                return False
        date = subprocess.run(["git", "-C", repo_dir,
                    "for-each-ref", "--sort=-authordate", "--count=1", "--format='%(authordate:iso8601)'"],
                   stdout=subprocess.PIPE)
        os.makedirs(join(repo_dir, "info/web/"), exist_ok=True)
        with open(join(repo_dir, "info/web/last-modified"), "wb") as f:
            f.write(date.stdout)
        description_file = os.path.join(repo_dir, "description")
        export_file = os.path.join(repo_dir, "git-daemon-export-ok")

        self.description(description_file, repository["descriptions"])
        self.export(export_file)
        return True

    def export(self, export_file):
        """
        Mark a repository as exportable.

        :param export_file: the path to the git-daemon-export-ok file
        """
        if not exists(export_file):
            open(export_file, "a").close()

    def description(self, description_file, description):
        """
        Update a description file for a git repo.

        :param description_file: the path to the description file
        :param description: the description for this repo
        """

        if description is not None:
            with open(description_file, "wb") as f:
                f.write(description.encode("utf8") + b"\n")

    def get_local_repositories(self, data_dir):
        if not data_dir or not exists(data_dir):
            raise MirrorError("No input data directory")
        names = os.listdir(data_dir)
        local_repositories = []
        for name in names:
            source_path = join(data_dir, name)
            files = os.listdir(source_path)
            for file in files:
                if file.endswith(".git") and file != ".git":
                    local_repositories.append(normpath(abspath(join(source_path, file))).replace('\\','/'))
        return local_repositories

    def get_remote_repositories(self, database):
        if not database:
            raise MirrorError("No input database")
        try:
            store = RepositoryStore(self.setting)
            repositories = store.get_repository_list(database)
        except Exception as e:
            raise MirrorError("Read repository source failed: {}".format(str(e)))
        finally:
            del store
        return repositories

    def process_error(self, error):
        self.failed_list.append(error)
        print(error)

    def sync(self, data_dir='', database='', status_path='', consistency=False):
        """
        For each repo in the file, either update it if it is already mirrored, or
        mirror it

        :param data_dir: the git store path
        :param repositories_sources: sources to synchronize
        :param database: database file
        :param status_path: path to save status file
        :param consistency: delete remotely deleted repositories from our local mirror
        """

        local_repositories = self.get_local_repositories(data_dir)
        remote_repositories = self.get_remote_repositories(database)

        store = RepositoryStore(self.setting)

        self.failed_list = []
        for repository in remote_repositories:
            if self.mirror(data_dir, repository):
                store.update_update_time(database, repository['id'])

        remote_repositories = [self.get_repository_path(data_dir, remote_repo)
                               for remote_repo in self.get_remote_repositories(database)]
        if consistency:
            repos_to_move = [repo for repo in local_repositories if repo not in remote_repositories]
            backup_dir = join(self.setting['BACKUP_DIR'],'repositories')
            for repo in repos_to_move:
                repo_name = basename(repo)
                source_name = basename(dirname(repo))
                dst = join(join(backup_dir, source_name), repo_name)
                shutil.move(repo, dst)
                self.logger.info("Move to backup: {}".format(repo_name))

        if status_path:
            name = ''
            if database:
                name = basename(database).split('.')[0]
            self.save_status(status_path, name)

    def save_status(self, path='', name=''):
        """
        Export repo list to json file

        :param data: data to save
        :param file_name: file name to save
        """

        if not self.failed_list or not path:
            return
        # process failed list
        time_str = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        result = {
            "generatedAt": time_str,
            "status": self.failed_list
        }
        name = name if name else self.__class__.__name__.lower()
        file_name = '_'.join(('mirror',name, time_str)) + '.json'
        file = os.path.join(path, file_name)
        with open(file, 'w', encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

    def generate_cgitrc(self, data_dir='', database='', cgit_url='', cgitrc_file=''):
        local_repositories = self.get_local_repositories(data_dir)
        remote_repositories = self.get_remote_repositories(database)

        cgitrc = []
        recorded = []
        for repository in remote_repositories:
            repo_path = self.get_repository_path(data_dir, repository)
            if repo_path in local_repositories:
                name = repository['name']
                if name not in recorded:
                    url = name
                    recorded.append(name)
                else:
                    url = '.'.join(repository['owner'], name)
                if cgit_url:
                    cgit_url = cgit_url if cgit_url.endswith('/') else cgit_url + '/'
                    local_url = cgit_url + url
                    clone_url = "repo.clone-url={} {}\n".format(local_url, repository["clone_url"].split(',')[0])
                else:
                    clone_url = "repo.clone-url={}\n".format(repository["clone_url"].split(',')[0])
                cgitrc.append('repo.url={}\n'.format(url))
                cgitrc.append('repo.name={}\n'.format(repository['name']))
                cgitrc.append('repo.desc={}\n'.format(repository['descriptions']))
                cgitrc.append('repo.owner={}\n'.format(repository["owner"]))
                cgitrc.append('repo.section={}\n'.format(repository["section"]))
                cgitrc.append('repo.path={}\n'.format(self.get_repository_path(data_dir, repository)))
                cgitrc.append(clone_url)
                cgitrc.append('repo.homepage={}\n'.format(repository['html_url']))
                cgitrc.append('\n')

        cgitrc = "".join(cgitrc)
        with open(cgitrc_file, "w", encoding="utf-8") as f:
            f.write(cgitrc)


