# -*- coding: utf-8 -*-
""" Test case to install same app for multiple users on the same device at the same time
    https://jira.wdmv.wdc.com/browse/KAM-32323
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from app_manager_scripts.install_app import InstallApp
from platform_libraries.test_thread import MultipleThreadExecutor


class ConcurrentInstallSameAppMultipleUsers(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32323 - Install same app for multiple users on the same device at the same time'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32323'
    PRIORITY = 'Major'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.check_app_install = False
        self.app_id = None

    def before_test(self):
        env_dict = self.env.dump_to_dict()
        env_dict.pop('_testcase')
        env_dict['Settings'] = ['serial_client=False']
        
        # For admin user import
        env_dict['app_id'] = self.app_id
        env_dict['check_app_install'] = self.check_app_install
        self.install_app = InstallApp(env_dict)
        self.install_app.before_test()

        # For Second user import
        replace_username = self.env.username.rsplit('@')[0]
        username = self.env.username.replace(replace_username, replace_username + '+1')
        self.log.info("Second user email = '{}'".format(username))
        env_dict['username'] = username
        self.install_app1 = InstallApp(env_dict)
        self.install_app1.before_test()

    def test(self):
        self.log.info('Start to install app({}) by admin user and second user at the same time'
            .format(self.app_id))
        self.concurrent_install_app()
        self.log.info("*** Install same app for multiple users on the same device at the same time, Test PASSED !!!")

    def concurrent_install_app(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        mte.append_thread_by_func(target=self.install_app.test)
        mte.append_thread_by_func(target=self.install_app1.test)
        mte.run_threads()

    def after_test(self):
        self.install_app.uninstall_app = True
        self.install_app.after_test()
        self.install_app1.uninstall_app = True
        self.install_app1.after_test()

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Install same app for multiple users on the same device at the same time test ***
        Examples: ./start.sh app_manager_scripts/concur_install_same_app_multiple_users.py -ip 10.92.234.16 -env qa1
        --app_id com.wdc.importapp.ibi
        """)

    parser.add_argument('-appid', '--app_id', help='First App ID to installed')
    parser.add_argument('-chkapp', '--check_app_install', help='Remove app before start install app test', action='store_true')
    
    test = ConcurrentInstallSameAppMultipleUsers(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)