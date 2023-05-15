# -*- coding: utf-8 -*-
""" Test case to install different app for multiple users on the same device at the same time
    https://jira.wdmv.wdc.com/browse/KAM-32537
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


class ConcurrentInstallDifferentAppMultipleUsers(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32537 - Install different app for multiple users on the same device'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32537'
    PRIORITY = 'Major'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.check_app_install = False
        self.app_id_1 = None
        self.app_id_2 = None

    def before_test(self):
        env_dict = self.env.dump_to_dict()
        env_dict.pop('_testcase')
        env_dict['check_app_install'] = self.check_app_install
        env_dict['Settings'] = ['serial_client=False']
        
        # For admin user import
        env_dict['app_id'] = self.app_id_1
        self.install_app = InstallApp(env_dict)
        self.install_app.before_test()

        # For Second user import
        replace_username = self.env.username.rsplit('@')[0]
        username = self.env.username.replace(replace_username, replace_username + '+1')
        self.log.info("Second user email = '{}'".format(username))
        env_dict['username'] = username
        env_dict['app_id'] = self.app_id_2
        self.install_app1 = InstallApp(env_dict)
        self.install_app1.before_test()

    def test(self):
        self.log.info('Start to install app({0}) by admin user and install app({1}) by second user at the same time'
            .format(self.app_id_1, self.app_id_2))
        self.concurrent_install_app()
        self.log.info("*** Install different app for multiple users on the same device, Test PASSED !!!")

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
        *** Install different app for multiple users on the same device at the same time test ***
        Examples: ./start.sh app_manager_scripts/concur_install_different_app_multiple_users.py -ip 10.92.234.16 -env qa1
        --app_id_1 com.wdc.importapp.ibi --app_id_2 com.elephantdrive.ibi
        """)

    parser.add_argument('-appid1', '--app_id_1', help='First App ID to installed')
    parser.add_argument('-appid2', '--app_id_2', help='Second App ID to installed')
    parser.add_argument('-chkapp', '--check_app_install', help='Remove app before start install app test', action='store_true')
    
    test = ConcurrentInstallDifferentAppMultipleUsers(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)