# -*- coding: utf-8 -*-
""" Test case to install and uninstall app at the same time for multiple users - different app
    https://jira.wdmv.wdc.com/browse/KAM-32613
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from app_manager_scripts.install_app import InstallApp
from app_manager_scripts.uninstall_app import UninstallApp
from platform_libraries.test_thread import MultipleThreadExecutor


class ConcurrentInstallUninstallAppMultipleUsersDifferentApp(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32613 - Install and uninstall app at the same time for multiple users - different app'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32613'
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
        env_dict['Settings'] = ['serial_client=False']
        
        # For admin user import
        env_dict['app_id'] = self.app_id_1
        env_dict['check_app_install'] = self.check_app_install
        setattr(self, 'install_app', InstallApp(env_dict))
        getattr(self, 'install_app').before_test()
        setattr(self, 'uninstall_app', UninstallApp(env_dict))

        # For Second user import
        replace_username = self.env.username.rsplit('@')[0]
        username = self.env.username.replace(replace_username, replace_username + '+1')
        self.log.info("Second user email = '{}'".format(username))
        env_dict['username'] = username
        env_dict['app_id'] = self.app_id_2
        env_dict['check_app_install'] = self.check_app_install
        setattr(self, 'install_app1', InstallApp(env_dict))
        getattr(self, 'install_app1').before_test()
        setattr(self, 'uninstall_app1', UninstallApp(env_dict))

    def test(self):
        self.log.info('Start to install app({}) by admin user'.format(self.app_id_1))
        self.install_app.test()
        self.log.info('Clean up logcat to let concurrent_install_uninstall logs clear.')
        self.adb.clean_logcat()
        time.sleep(10)
        self.log.info('Start to uninstall app({0}) by admin user and install app({1}) by second user at the same time'
            .format(self.app_id_1, self.app_id_2))
        self.concurrent_install_uninstall()
        self.log.info("*** Install and uninstall app at the same time for multiple users - different app, Test PASSED !!!")

    def concurrent_install_uninstall(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        mte.append_thread_by_func(target=self.uninstall_app.test)
        mte.append_thread_by_func(target=self.install_app1.test)
        mte.run_threads()

    def after_test(self):
        self.uninstall_app1.test()

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Install and uninstall different app at the same time for multiple users test ***
        Examples: ./start.sh app_manager_scripts/concur_install_uninstall_multiple_users_different_app.py -ip 10.92.234.16 -env qa1
        --app_id_1 com.wdc.importapp.ibi --app_id_2 com.elephantdrive.ibi
        """)

    parser.add_argument('-appid1', '--app_id_1', help='First App ID to installed')
    parser.add_argument('-appid2', '--app_id_2', help='Second App ID to installed')
    parser.add_argument('-chkapp', '--check_app_install', help='Remove app before start install app test', action='store_true')
    
    test = ConcurrentInstallUninstallAppMultipleUsersDifferentApp(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)