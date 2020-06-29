#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from os.path import join, dirname, abspath


class Setting:
    def __init__(self):
        self.attribute = {
            "CMD": abspath(join(dirname(dirname(abspath(__file__))), "gitmirror.py")),
            "VERSION": join(dirname(dirname(abspath(__file__))), "VERSION"),
            "GITHUB_TOKEN": join(dirname(dirname(abspath(__file__))), "github_token"),
            "GITEE_TOKEN": join(dirname(dirname(abspath(__file__))), "gitee_token"),
            "LOG_ENABLED": True,
            "LOG_FORMAT": '%(asctime)s:%(name)s:%(levelname)s:%(message)s',
            "LOG_LEVEL": 'DEBUG',
            "LOG_FILE": None,
            "LOG_DIR": join(dirname(dirname(abspath(__file__))), "log"),
            "REQUESTS_CONNECTION_TIMEOUT": 3,
            "REQUESTS_READ_TIMEOUT": 10,
            "REQUESTS_RETRY_ENABLED": False,
            "REQUESTS_RETRY_TIMES": 3,
            "REQUESTS_RETRY_INTERVAL": 3,
            "ENABLE_DEFAULT_SECTION": True,
            "DEFAULT_SECTION_NAME": "Unclassified",
            "GIT_LOW_SPEED": 1000,
            "GIT_LOW_TIMEOUT": 60,
            "DATABASE_DIR": join(dirname(dirname(abspath(__file__))), "database"),
            "BACKUP_DIR": join(dirname(dirname(abspath(__file__))), "backup"),
            "DB_BACKUP_DIR": join(dirname(dirname(abspath(__file__))), "backup/database"),
            "REPOS_BACKUP_DIR": join(dirname(dirname(abspath(__file__))), "backup/repositories"),
            "DATA_DIR": '/srv/git',
            "CRON_FILE": join(dirname(dirname(abspath(__file__))), "crontab")
        }

    def __getitem__(self, name):
        return self.attribute[name]

    def __setitem__(self, name, value):
        self.attribute[name] = value

    def __contains__(self, name):
        return name in self.attribute

    def __iter__(self):
        return iter(self.attribute)

    def __len__(self):
        return len(self.attribute)
