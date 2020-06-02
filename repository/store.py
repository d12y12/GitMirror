#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from os.path import exists, basename
import logging
from .minisetting import Setting


class Repository:
    def __init__(self):
        self.repository = {
            "name": '',
            "section": '',
            "owner": '',
            "descriptions": '',
            "html_url": '',
            "clone_url": '',
            "target_url": '',
            "source": '',
            "source_type": ''
        }

    def __getitem__(self, name):
        return self.repository[name]

    def __setitem__(self, name, value):
        self.repository[name] = value

    def __contains__(self, name):
        return name in self.repository

    def __iter__(self):
        return iter(self.repository)

    def __len__(self):
        return len(self.repository)

    def to_dict(self):
        return self.repository

    def to_tuple(self):
        return tuple(self.repository.values())


class Configuration:
    def __init__(self):
        self.configuration = {
            "service_name": '',
            "host": '',
            "consistency": '',
            "crontab": '',
            "repositories": '',
            "original_sql": ''
        }

    def __getitem__(self, name):
        return self.configuration[name]

    def __setitem__(self, name, value):
        self.configuration[name] = value

    def __contains__(self, name):
        return name in self.configuration

    def __iter__(self):
        return iter(self.configuration)

    def __len__(self):
        return len(self.configuration)

    def to_dict(self):
        return self.configuration

    def to_tuple(self):
        return tuple(self.configuration.values())


class DatabaseError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class RepositoryStore:
    def __init__(self, setting: Setting = None, logger=None):
        self.setting = Setting() if not setting else setting
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.sqlite_file = ''
        self.sqlite_connection = None

    def open(self, path):
        if exists(path):
            if self.sqlite_connection:
                self.close()
            try:
                self.sqlite_file = path
                self.sqlite_connection = sqlite3.connect(self.sqlite_file)
                self.logger.debug("数据库连接<{}>已打开".format(basename(self.sqlite_file)))
            except sqlite3.Error as error:
                self.logger.error("数据库出错啦: %s", error)
        else:
            self.logger.debug("数据库文件: %s 不存在", path)

    def close(self):
        if self.sqlite_connection:
            self.sqlite_connection.close()
            self.sqlite_connection = None
            self.logger.debug("数据库连接<{}>已关闭".format(basename(self.sqlite_file)))

    def create(self, sql_file, sqlite_file):
        if not exists(sql_file):
            raise ValueError("SQL文件: {} 不存在".format(sql_file))
        if exists(sqlite_file):
            raise ValueError("SQL文件: {} 已存在，使用<open>函数打开".format(basename(sqlite_file)))
        try:
            self.sqlite_file = sqlite_file
            self.sqlite_connection = sqlite3.connect(sqlite_file)
            with open(sql_file, 'r') as f:
                sql_script = f.read()
            cursor = self.sqlite_connection.cursor()
            cursor.executescript(sql_script)
            cursor.close()
            self.logger.debug("数据库<{}>创建成功".format(basename(sqlite_file)))
        except sqlite3.Error as error:
            self.logger.error("数据库出错啦: %s", error)
            raise DatabaseError("{}".format(error))
        finally:
            self.close()

    def add_repository(self, sqlite_file, repository: Repository):
        self.open(sqlite_file)
        ret = None
        try:
            self.logger.debug("add_repository: {}".format(repository.to_dict()))
            cursor = self.sqlite_connection.cursor()
            sqlite_insert_query = "INSERT INTO Repositories(name, section, owner, descriptions, html_url, " \
                                  "clone_url, target_url, source, source_type, last_check) " \
                                  "VALUES(?,?,?,?,?,?,?,?,?,datetime('now','localtime'))"
            cursor.execute(sqlite_insert_query, repository.to_tuple())
            self.sqlite_connection.commit()
            repository_id = cursor.lastrowid
            cursor.close()
            ret = repository_id
        except sqlite3.Error as error:
            if "UNIQUE constraint failed" in str(error):
                duplicate = self.find_duplicate(sqlite_file, repository)
                duplicate_id = duplicate['id']
                del duplicate['id']
                del duplicate['last_update']
                del duplicate['last_check']
                if duplicate['source_type'] == 'repository' and repository['source_type'] == 'index':
                    self.merge_duplicate(sqlite_file, duplicate_id, repository)
                    ret = {'merger': duplicate}
                elif duplicate == repository.to_dict():
                    self.update_check_time(sqlite_file, duplicate_id)
                    ret = duplicate_id
                else:
                    ret = {'duplicate': duplicate}
            else:
                ret = 'write to database failed {}'.format(error)
                self.logger.error("写入数据库出错啦: %s %s", repository['name'], error)
        finally:
            self.close()
            return ret

    def merge_duplicate(self, sqlite_file, merge_repository_id, repository: Repository):
        self.open(sqlite_file)
        try:
            self.logger.debug("merge_duplicate: %d", merge_repository_id)
            cursor = self.sqlite_connection.cursor()
            sqlite_update_query = "UPDATE Repositories SET name=?, section=?, owner=?, descriptions=?, html_url=?, " \
                                  "clone_url=?, target_url=?, source=?, source_type=?," \
                                  "last_check=datetime('now','localtime') WHERE id=?"
            cursor.execute(sqlite_update_query, repository.to_tuple()+(str(merge_repository_id),))
            self.sqlite_connection.commit()
            cursor.close()
        except sqlite3.Error as error:
            self.logger.error("数据库出错啦: %s", error)
        finally:
            self.close()

    def update_time(self, sqlite_file, name: str, repository_id: int):
        self.open(sqlite_file)
        try:
            self.logger.debug("update_{}_time: {}".format(name, repository_id))
            cursor = self.sqlite_connection.cursor()
            sqlite_update_query = "UPDATE Repositories SET {}=datetime('now','localtime') WHERE id=?".format(name)
            cursor.execute(sqlite_update_query, (str(repository_id),))
            self.sqlite_connection.commit()
            cursor.close()
        except sqlite3.Error as error:
            self.logger.error("数据库出错啦: %s", error)
        finally:
            self.close()

    def update_check_time(self, sqlite_file, repository_id: int):
        self.update_time(sqlite_file, 'last_check', repository_id)

    def update_update_time(self, sqlite_file, repository_id: int):
        self.update_time(sqlite_file, 'last_update', repository_id)

    def find_duplicate(self, sqlite_file, repository: Repository):
        self.open(sqlite_file)
        ret = {}
        try:
            self.logger.debug("find_duplicate: {}".format(repository.to_dict()))
            self.sqlite_connection.row_factory = sqlite3.Row
            cursor = self.sqlite_connection.cursor()
            sqlite_select_query = "SELECT * FROM Repositories WHERE clone_url=? "
            cursor.execute(sqlite_select_query, (repository['clone_url'],))
            record = cursor.fetchone()
            cursor.close()
            if record:
                ret = dict(record)
        except sqlite3.Error as error:
            self.logger.error("数据库出错啦: %s", error)
        finally:
            self.close()
            return ret

    def get_repository_list_by_source(self, sqlite_file, source: str):
        self.open(sqlite_file)
        ret = []
        try:
            self.logger.debug("get_repository_list_by_source: {}".format(source))
            self.sqlite_connection.row_factory = sqlite3.Row
            cursor = self.sqlite_connection.cursor()
            sqlite_select_query = "SELECT * FROM Repositories WHERE source=? "
            cursor.execute(sqlite_select_query, (source,))
            records = cursor.fetchall()
            cursor.close()
            if records:
                ret = [dict(row) for row in records]
        except sqlite3.Error as error:
            self.logger.error("数据库出错啦: %s", error)
        finally:
            self.close()
            return ret

    def get_repository_list(self, sqlite_file):
        self.open(sqlite_file)
        ret = []
        try:
            self.sqlite_connection.row_factory = sqlite3.Row
            cursor = self.sqlite_connection.cursor()
            sqlite_select_query = "SELECT * FROM Repositories"
            cursor.execute(sqlite_select_query)
            records = cursor.fetchall()
            if records:
                ret = [dict(row) for row in records]
            cursor.close()
        except sqlite3.Error as error:
            self.logger.error("数据库出错啦: %s", error)
        finally:
            self.close()
            return ret

    def get_sources_list(self):
        try:
            self.sqlite_connection.row_factory = sqlite3.Row
            cursor = self.sqlite_connection.cursor()
            sqlite_select_query = "SELECT DISTINCT source, source_type FROM Repositories"
            cursor.execute(sqlite_select_query)
            records = cursor.fetchall()
            sources_list = []
            if records:
                for record in records:
                    source = dict(record)
                    sources_list.append(source)
            cursor.close()
            return sources_list
        except sqlite3.Error as error:
            self.logger.error("数据库出错啦: %s", error)

    def get_config(self, sqlite_file: str, name: str):
        self.open(sqlite_file)
        ret = ''
        try:
            self.logger.debug("get <{}> form <{}>".format(name, basename(sqlite_file)))
            cursor = self.sqlite_connection.cursor()
            sqlite_select_query = "Select {} from Configurations".format(name)
            cursor.execute(sqlite_select_query)
            record = cursor.fetchone()
            cursor.close()
            ret = record[0]
        except sqlite3.Error as error:
            self.logger.error("数据库出错啦: %s", error)
            raise DatabaseError("{}".format(error))
        finally:
            self.close()
            return ret

    def get_repositories(self, sqlite_file: str):
        return self.get_config(sqlite_file, 'repositories')

    def get_host(self, sqlite_file: str):
        return self.get_config(sqlite_file, 'host')

    def get_original_sql(self, sqlite_file: str):
        return self.get_config(sqlite_file, 'original_sql')
    
    def get_crontab(self, sqlite_file: str):
        return self.get_config(sqlite_file, 'crontab')

    def update_config(self, sqlite_file: str, name: str, value):
        self.open(sqlite_file)
        try:
            self.logger.debug("update <{}> into <{}> with <{}>".format(name, basename(sqlite_file), value))
            cursor = self.sqlite_connection.cursor()
            sqlite_update_query = "UPDATE Configurations SET {}=?".format(name)
            cursor.execute(sqlite_update_query, (value,))
            self.sqlite_connection.commit()
            cursor.close()
        except sqlite3.Error as error:
            self.logger.error("数据库出错啦: %s", error)
            raise DatabaseError("{}".format(error))
        finally:
            self.close()

    def update_original_sql(self, sqlite_file: str, file_name: str):
        self.update_config(sqlite_file, 'original_sql', file_name)
    
    def get_full_config(self, sqlite_file: str):
        self.open(sqlite_file)
        ret = {}
        try:
            self.sqlite_connection.row_factory = sqlite3.Row
            cursor = self.sqlite_connection.cursor()
            sqlite_select_query = "SELECT * FROM Configurations"
            cursor.execute(sqlite_select_query)
            record = cursor.fetchone()
            if record:
                ret = dict(record)
            cursor.close()
        except sqlite3.Error as error:
            self.logger.error("数据库出错啦: %s", error)
        finally:
            self.close()
            return ret
