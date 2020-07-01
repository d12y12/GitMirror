import unittest
from os.path import join, dirname, abspath, exists, isdir, normpath
from shutil import copy, rmtree
from os import remove, listdir
import string
import filecmp
import sys
sys.path.insert(0, '..')
from repository import RepositoryManager
from repository.minisetting import Setting
import time

class  ServicesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.setting = Setting()
        cls.setting['LOG_ENABLED'] = False
        cls.repo_manager = RepositoryManager(cls.setting)
        cls.test_data_dir = join(dirname(abspath(__file__)), "test_data")
        cls.dst_dir = cls.setting['DATABASE_DIR']
        cls.backup_dir = cls.setting['DB_BACKUP_DIR']
    
    
    def test_1_get_empty_service_list(self):
        # test 1 get empty services list
        services, services_possible = self.repo_manager.get_services_list()
        self.assertFalse(services)
        self.assertFalse(services_possible)
    
    def test_2_add_services(self):
        # test 2 add 1 service github and 1 sql yocto
        copy(join(self.test_data_dir, "github.sql"), join(self.dst_dir, "github.sql"))
        copy(join(self.test_data_dir, "yocto.sql"), join(self.dst_dir, "yocto.sql"))
        copy(join(self.test_data_dir, "gitee.sql"), join(self.dst_dir, "gitee.sql"))
        self.repo_manager.add_service("github")
        services, services_possible = self.repo_manager.get_services_list()
        self.assertEqual(len(listdir(self.backup_dir)), 1)
        self.assertIn("github", services)
        self.assertNotIn("yocto", services)
        self.assertNotIn("gitee", services)
        self.assertIn("gitee", services_possible)
        self.assertIn("yocto", services_possible)
        self.assertNotIn("github", services_possible)

        # test 3 add service yocto
        self.repo_manager.add_service("yocto")
        services, services_possible = self.repo_manager.get_services_list()
        self.assertEqual(len(listdir(self.backup_dir)), 2)
        self.assertIn("github", services)
        self.assertIn("yocto", services)
        self.assertNotIn("gitee", services)
        self.assertIn("gitee", services_possible)
        self.assertNotIn("github", services_possible)
        self.assertNotIn("yocto", services_possible)

        # test 4 add service gitee
        self.repo_manager.add_service("gitee")
        services, services_possible = self.repo_manager.get_services_list()
        self.assertEqual(len(listdir(self.backup_dir)), 3)
        self.assertIn("github", services)
        self.assertIn("yocto", services)
        self.assertIn("gitee", services)
        self.assertFalse(services_possible)

    def test_3_add_duplicate_service(self):
        # test 5 add duplicate service github
        copy(join(self.test_data_dir, "github.sql"), join(self.dst_dir, "github.sql"))
        self.repo_manager.add_service("github")
        services, services_possible = self.repo_manager.get_services_list()
        self.assertEqual(len(listdir(self.backup_dir)), 3)
        self.assertIn("github", services)
        self.assertIn("yocto", services)
        self.assertFalse(services_possible)

    def test_4_add_updated_service(self):
        # test 6 add updated service github
        time.sleep(1)
        copy(join(self.test_data_dir, "github_update.sql"), join(self.dst_dir, "github.sql"))
        self.repo_manager.add_service("github")
        services, services_possible = self.repo_manager.get_services_list()
        self.assertEqual(len(listdir(self.backup_dir)), 5)
        self.assertIn("github", services)
        self.assertIn("yocto", services)
        self.assertFalse(services_possible)
    
    def test_5_cron_file(self):
        # test 7 generate cron file
        cron_template = join(self.test_data_dir, 'crontab_template')
        with open(cron_template, 'rb') as fp:
            raw = fp.read().decode('utf8')

        project_dir = normpath(abspath(dirname(dirname(abspath(__file__)))))
        content = string.Template(raw).safe_substitute(project_dir=project_dir)

        ref_conf_file = join(dirname(dirname(abspath(__file__))), 'crontab_ref')
        with open(ref_conf_file, 'wb') as fp:
            fp.write(content.encode('utf8'))
        self.repo_manager.set_crontab()
        self.assertTrue(filecmp.cmp(ref_conf_file, self.setting['CRON_FILE']))
        remove(ref_conf_file)
        remove(self.setting['CRON_FILE'])

    def test_6_remove_services(self):
        # test 8 remove service yocto
        self.repo_manager.remove_service("yocto")
        services, services_possible = self.repo_manager.get_services_list()
        self.assertEqual(len(listdir(self.backup_dir)), 6)
        self.assertIn("github", services)
        self.assertIn("gitee", services)
        self.assertNotIn("yocto", services)
        self.assertFalse(services_possible)

        # test 7 remove service github
        self.repo_manager.remove_service("github")
        services, services_possible = self.repo_manager.get_services_list()
        self.assertEqual(len(listdir(self.backup_dir)), 7)
        self.assertIn("gitee", services)
        self.assertNotIn("github", services)
        self.assertNotIn("yocto", services)
        self.assertFalse(services_possible)

        # test 8 remove service gitee
        self.repo_manager.remove_service("gitee")
        services, services_possible = self.repo_manager.get_services_list()
        self.assertEqual(len(listdir(self.backup_dir)), 8)
        self.assertNotIn("gitee", services)
        self.assertNotIn("github", services)
        self.assertNotIn("yocto", services)
        self.assertFalse(services_possible)

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
        if exists(cls.setting['CRON_FILE']):
            remove(cls.setting['CRON_FILE'])
        if exists(join(dirname(dirname(abspath(__file__))), 'crontab_ref')):
            remove(join(dirname(dirname(abspath(__file__))), 'crontab_ref'))

if __name__ == '__main__':
    unittest.main()
