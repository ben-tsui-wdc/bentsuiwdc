# -*- coding: utf-8 -*-
""" Test case to install and uninstall different app at the same time for a second user
    https://jira.wdmv.wdc.com/browse/KAM-32615
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


class ConcurrentInstallUninstallDifferentAppSecondUser(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32615 - Install and uninstall different app at the same time for a second user'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32615'
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

        # For second user import and new different object for different app install/uninstall
        replace_username = self.env.username.rsplit('@')[0]
        username = self.env.username.replace(replace_username, replace_username + '+1')
        self.log.info("Second user email = '{}'".format(username))
        env_dict['username'] = username
        env_dict['check_app_install'] = self.check_app_install
        env_dict['app_id'] = self.app_id_1
        self.install_app1 = InstallApp(env_dict)
        self.uninstall_app1 = UninstallApp(env_dict)
        env_dict['app_id'] = self.app_id_2
        self.install_app2 = InstallApp(env_dict)
        self.uninstall_app2 = UninstallApp(env_dict)
        self.install_app1.before_test()
        self.install_app2.before_test()

    def test(self):
        self.log.info('Start to install app({}) by second user'.format(self.app_id_1))
        self.install_app1.test()
        self.log.info('Clean up logcat to let concurrent_install_uninstall logs clear.')
        self.adb.clean_logcat()
        time.sleep(10)
        self.log.info('Start to uninstall app({0}) and install app({1}) by second user at the same time'
            .format(self.app_id_1, self.app_id_2))
        self.concurrent_install_uninstall()
        self.log.info("*** Install and uninstall different app at the same time for a second user, Test PASSED !!!")

    def concurrent_install_uninstall(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        mte.append_thread_by_func(target=self.uninstall_app1.test)
        mte.append_thread_by_func(target=self.install_app2.test)
        mte.run_threads()

    def after_test(self):
        self.uninstall_app2.test()

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Install and uninstall different app at the same time for a second user test ***
        Examples: ./start.sh app_manager_scripts/concur_install_uninstall_different_app_second_user.py -ip 10.92.234.16 -env qa1
        --app_id_1 com.wdc.importapp.ibi --app_id_2 com.elephantdrive.ibi
        """)

    parser.add_argument('-appid1', '--app_id_1', help='First App ID to installed')
    parser.add_argument('-appid2', '--app_id_2', help='Second App ID to installed')
    parser.add_argument('-chkapp', '--check_app_install', help='Remove app before start install app test', action='store_true')
    
    test = ConcurrentInstallUninstallDifferentAppSecondUser(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)