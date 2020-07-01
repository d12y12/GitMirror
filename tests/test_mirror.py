import unittest
import os
from os.path import join, dirname, abspath, exists, isdir
from shutil import copy, rmtree
from os import remove, listdir
from hashlib import md5
import json
import filecmp
import sys
sys.path.insert(0, '..')
from repository import RepositoryManager
from repository.minisetting import Setting
import time

def onerror(func, path, exc_info):
    """
    Error handler for ``shutil.rmtree``.

    If the error is due to an access error (read only file)
    it attempts to add write permission and then retries.

    If the error is for another reason it re-raises the error.

    Usage : ``shutil.rmtree(path, onerror=onerror)``
    """
    import stat
    if not os.access(path, os.W_OK):
        # Is the error an access error ?
        os.chmod(path, stat.S_IWUSR)
        func(path)
    else:
        raise

class  MirrorTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.setting = Setting()
        # cls.setting['LOG_ENABLED'] = False
        cls.setting['DATA_DIR'] = join(dirname(dirname(abspath(__file__))), "data")
        cls.repo_manager = RepositoryManager(cls.setting)
        cls.test_data_dir = join(dirname(abspath(__file__)), "test_data")
        cls.dst_dir = cls.setting['DATABASE_DIR']
        cls.data_dir = cls.setting['DATA_DIR']

    
    def test_1_cgit_mirror(self):
        # test 1 cgit mirror
        copy(join(self.test_data_dir, "yocto.sql"), join(self.dst_dir, "yocto.sql"))
        self.repo_manager.add_service("yocto")
        services, services_possible = self.repo_manager.get_services_list()
        self.assertIn("yocto", services)
        repos = self.repo_manager.parse_service("yocto")
        # run twice, 1st for init, 2nd for update
        for num in range(0,2):
            self.repo_manager.mirror_service("yocto")
            self.assertTrue(exists(join(self.data_dir, 'yocto')))
            self.assertTrue(exists(join(
                self.data_dir,
                'yocto',
                md5("http://git.yoctoproject.org/cgit.cgi/crops/".encode()).hexdigest()
            )))
            self.assertTrue(exists(join(
                self.data_dir,
                'yocto',
                md5("http://git.yoctoproject.org/cgit.cgi/crops/".encode()).hexdigest(),
                'crops.git'
            )))
            self.assertTrue(filecmp.cmp(join(self.test_data_dir, 'yocto.repo'), 
                                        join(self.data_dir, 'yocto', 'yocto.repo')))

    def test_2_github_mirror(self):
        # test 2 github mirror
        copy(join(self.test_data_dir, "github.sql"), join(self.dst_dir, "github.sql"))
        self.repo_manager.add_service("github")
        services, services_possible = self.repo_manager.get_services_list()
        self.assertIn("github", services)
        repos = self.repo_manager.parse_service("github")
        # run twice, 1st for init, 2nd for update
        for num in range(0,2):
            self.repo_manager.mirror_service("github")
            self.assertTrue(exists(join(self.data_dir, 'github')))
            self.assertTrue(exists(join(
                self.data_dir,
                'github',
                md5("d12y12/temp".encode()).hexdigest()
            )))
            self.assertTrue(exists(join(
                self.data_dir,
                'github',
                md5("d12y12/temp".encode()).hexdigest(),
                'temp.git'
            )))
            self.assertTrue(filecmp.cmp(join(self.test_data_dir, 'github.repo'), 
                                        join(self.data_dir, 'github', 'github.repo')))

    def test_3_gitee_mirror(self):
        # test 3 github mirror
        copy(join(self.test_data_dir, "gitee.sql"), join(self.dst_dir, "gitee.sql"))
        self.repo_manager.add_service("gitee")
        services, services_possible = self.repo_manager.get_services_list()
        self.assertIn("gitee", services)
        repos = self.repo_manager.parse_service("gitee")
        # run twice, 1st for init, 2nd for update
        for num in range(0,2):
            self.repo_manager.mirror_service("gitee")
            self.assertTrue(exists(join(self.data_dir, 'gitee')))
            self.assertTrue(exists(join(
                self.data_dir,
                'gitee',
                md5("d12y12/temp".encode()).hexdigest()
            )))
            self.assertTrue(exists(join(
                self.data_dir,
                'gitee',
                md5("d12y12/temp".encode()).hexdigest(),
                'temp.git'
            )))
            self.assertTrue(filecmp.cmp(join(self.test_data_dir, 'gitee.repo'), 
                                        join(self.data_dir, 'gitee', 'gitee.repo')))

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
        for dst_dir in [cls.setting['BACKUP_DIR'], cls.setting['LOG_DIR'], cls.setting['DATA_DIR']]: 
            if exists(dst_dir):
                rmtree(dst_dir, onerror=onerror)

if __name__ == '__main__':
    unittest.main()
