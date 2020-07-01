import unittest
from os.path import join, dirname, abspath, exists, isdir
from shutil import copy, rmtree
from os import remove, listdir
import json
import time
import sys
sys.path.insert(0, '..')
from repository import RepositoryManager
from repository.minisetting import Setting


class  ParserTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.setting = Setting()
        # cls.setting['LOG_ENABLED'] = False
        cls.repo_manager = RepositoryManager(cls.setting)
        cls.test_data_dir = join(dirname(abspath(__file__)), "test_data")
        cls.dst_dir = cls.setting['DATABASE_DIR']

    
    def test_1_cgit_parser(self):
        # test 1 cgit parser
        copy(join(self.test_data_dir, "yocto_parser.sql"), join(self.dst_dir, "yocto.sql"))
        self.repo_manager.add_service("yocto")
        services, services_possible = self.repo_manager.get_services_list()
        self.assertIn("yocto", services)
        repos = self.repo_manager.parse_service("yocto")
        self.repo_manager.get_service_repos("yocto", "./yocto.json")
        with open("./yocto.json", "r", encoding='utf8') as data:
            repos_db = json.load(data)
        repos_db_reform = []
        for repo in repos_db:
            del repo['id']
            del repo['last_check']
            del repo['last_update']
            repos_db_reform.append(repo)
        self.assertEqual(repos, repos_db_reform)
        remove("./yocto.json")
        log_dir = self.setting['LOG_DIR']
        self.assertTrue(0 <= len(listdir(log_dir)) <= 1)
        for sub_file in listdir(log_dir):
            sub_file = join(log_dir, sub_file)
            with open(sub_file, "r", encoding='utf8') as data:
                log_data = json.load(data)
            if 'status' in log_data:
                for source, status in log_data['status'].items():
                    if 'error' in status:
                        self.assertTrue('exclude' in status['error'] or 'download failed:' in status['error'])

    def test_2_github_parser(self):
        copy(join(self.test_data_dir, "github_parser.sql"), join(self.dst_dir, "github.sql"))
        self.repo_manager.add_service("github")
        services, services_possible = self.repo_manager.get_services_list()
        self.assertIn("github", services)
        repos = self.repo_manager.parse_service("github")
        self.repo_manager.get_service_repos("github", "./github.json")
        with open("./github.json", "r", encoding='utf8') as data:
            repos_db = json.load(data)
        repos_db_reform = []
        for repo in repos_db:
            del repo['id']
            del repo['last_check']
            del repo['last_update']
            repos_db_reform.append(repo)
        self.assertEqual(repos, repos_db_reform)
        remove("./github.json")
        log_dir = self.setting['LOG_DIR']
        self.assertTrue(0 <= len(listdir(log_dir)) <= 1)
        for sub_file in listdir(log_dir):
            sub_file = join(log_dir, sub_file)
            with open(sub_file, "r", encoding='utf8') as data:
                log_data = json.load(data)
            if 'status' in log_data:
                for source, status in log_data['status'].items():
                    if 'error' in status:
                        self.assertTrue('exclude' in status['error'] or 'download failed:' in status['error'])

    def test_3_gitee_parser(self):
        copy(join(self.test_data_dir, "gitee_parser.sql"), join(self.dst_dir, "gitee.sql"))
        self.repo_manager.add_service("gitee")
        services, services_possible = self.repo_manager.get_services_list()
        self.assertIn("gitee", services)
        repos = self.repo_manager.parse_service("gitee")
        self.repo_manager.get_service_repos("gitee", "./gitee.json")
        with open("./gitee.json", "r", encoding='utf8') as data:
            repos_db = json.load(data)
        repos_db_reform = []
        for repo in repos_db:
            del repo['id']
            del repo['last_check']
            del repo['last_update']
            repos_db_reform.append(repo)
        self.assertEqual(repos, repos_db_reform)
        remove("./gitee.json")
        log_dir = self.setting['LOG_DIR']
        self.assertTrue(0 <= len(listdir(log_dir)) <= 1)
        for sub_file in listdir(log_dir):
            sub_file = join(log_dir, sub_file)
            with open(sub_file, "r", encoding='utf8') as data:
                log_data = json.load(data)
            if 'status' in log_data:
                for source, status in log_data['status'].items():
                    if 'error' in status:
                        self.assertTrue('exclude' in status['error'] or 'download failed:' in status['error'])

    @classmethod
    def tearDownClass(cls):
        dst_dir = cls.setting['DATABASE_DIR']
        for sub_dir in listdir(dst_dir):
            if sub_dir == 'example':
                continue
            sub_dir = join(dst_dir, sub_dir)
            if isdir(sub_dir):
                rmtree(sub_dir)
            else:
                remove(sub_dir)
        dst_dir = cls.setting['BACKUP_DIR']
        if exists(dst_dir):
            rmtree(dst_dir)
        dst_dir = cls.setting['LOG_DIR']
        if exists(dst_dir):
            rmtree(dst_dir)

if __name__ == '__main__':
    unittest.main()
