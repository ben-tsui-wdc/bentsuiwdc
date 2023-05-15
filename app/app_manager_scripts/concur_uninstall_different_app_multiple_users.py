# -*- coding: utf-8 -*-
""" Test case to uninstall different app for multiple users on the same device at the same time
    https://jira.wdmv.wdc.com/browse/KAM-32538
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from app_manager_scripts.install_app import InstallApp
from app_manager_scripts.uninstall_app import UninstallApp
from platform_libraries.test_thread import MultipleThreadExecutor


class ConcurrentUninstallDifferentAppMultipleUsers(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32538 - Uninstall different app for multiple users on the same device'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32538'
    PRIORITY = 'Major'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.check_pm_list = False
        self.app_id_1 = None
        self.app_id_2 = None

    def before_test(self):
        env_dict = self.env.dump_to_dict()
        env_dict.pop('_testcase')
        env_dict['Settings'] = ['serial_client=False']
        
        # For admin user import
        env_dict['app_id'] = self.app_id_1
        env_dict['check_pm_list'] = self.check_pm_list
        setattr(self, 'install_app', InstallApp(env_dict))
        setattr(self, 'uninstall_app', UninstallApp(env_dict))

        # For Second user import
        replace_username = self.env.username.rsplit('@')[0]
        username = self.env.username.replace(replace_username, replace_username + '+1')
        self.log.info("Second user email = '{}'".format(username))
        env_dict['username'] = username
        env_dict['app_id'] = self.app_id_2
        env_dict['check_pm_list'] = self.check_pm_list
        setattr(self, 'install_app1', InstallApp(env_dict))
        setattr(self, 'uninstall_app1', UninstallApp(env_dict))

    def test(self):
        self.log.info('Prepare to install app1({0}) and app2({1}) first ...'.format(self.app_id_1, self.app_id_2))
        self.install_app.test()
        self.install_app1.test()
        self.log.info('Start to uninstall app({0}) by admin user and uninstall app({1}) by second user at the same time'
            .format(self.app_id_1, self.app_id_2))
        self.concurrent_uninstall_app()
        self.log.info("*** Uninstall different app for multiple users on the same device, Test PASSED !!!")

    def concurrent_uninstall_app(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        mte.append_thread_by_func(target=self.uninstall_app.test)
        mte.append_thread_by_func(target=self.uninstall_app1.test)
        mte.run_threads()

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Un-install different app for multiple users on the same device at the same time test ***
        Examples: ./start.sh app_manager_scripts/concur_uninstall_different_app_multiple_users.py -ip 10.92.234.16 -env qa1
        --app_id_1 com.wdc.importapp.ibi --app_id_2 com.elephantdrive.ibi
        """)

    parser.add_argument('-appid1', '--app_id_1', help='First App ID to installed')
    parser.add_argument('-appid2', '--app_id_2', help='Second App ID to installed')
    parser.add_argument('-chkpl', '--check_pm_list', help='Check pm list of app package', action='store_true')
    
    test = ConcurrentUninstallDifferentAppMultipleUsers(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)