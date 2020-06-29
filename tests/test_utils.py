import unittest
from os.path import join, dirname, abspath, exists
from os import remove
from shutil import copy
import sys
sys.path.insert(0, '..')
from repository.utils import get_token, get_version, set_logger, config_logging
from repository.minisetting import Setting


class  UtilsTest(unittest.TestCase):

    @classmethod  
    def setUpClass(cls):
        cls.setting = Setting()

    def test_1_get_version(self):
        with open(join(dirname(dirname(abspath(__file__))), "VERSION"), "r") as version_f:
            version_expect = version_f.read().strip()
        version = get_version()
        self.assertEqual(version, version_expect)
        version = get_version(self.setting)
        self.assertEqual(version, version_expect)

    def test_2_get_token(self):
        test_data_dir = join(dirname(abspath(__file__)), "test_data")
        dst_dir = dirname(dirname(abspath(__file__)))
        # test1 don't give token type
        token = get_token()
        self.assertFalse(token)
        # test2 no exist token file
        token = get_token(token_type='github')
        self.assertFalse(token)
        token = get_token(token_type='gitee')
        self.assertFalse(token)
        # test3 correct token file
        copy(join(test_data_dir, "test_token"), join(dst_dir, "github_token"))
        copy(join(test_data_dir, "test_token"), join(dst_dir, "gitee_token"))
        token = get_token(token_type='github')
        self.assertEqual(token, ("d12y12", "123456"))
        token = get_token(token_type='gitee')
        self.assertEqual(token, ("d12y12", "123456"))
        remove(join(dst_dir, "github_token"))
        remove(join(dst_dir, "gitee_token"))
        # test4 wrong token file
        copy(join(test_data_dir, "wrong_token1"), join(dst_dir, "github_token"))
        copy(join(test_data_dir, "wrong_token2"), join(dst_dir, "gitee_token"))
        token = get_token(token_type='github')
        self.assertFalse(token)
        token = get_token(token_type='gitee')
        self.assertFalse(token)
        remove(join(dst_dir, "github_token"))
        remove(join(dst_dir, "gitee_token"))

    @classmethod
    def tearDownClass(cls):
        dst_dir = dirname(dirname(abspath(__file__)))
        if exists(join(dst_dir, "github_token")):
            remove(join(dst_dir, "github_token"))
        if exists(join(dst_dir, "gitee_token")):
            remove(join(dst_dir, "gitee_token"))

if __name__ == '__main__':
    unittest.main()
