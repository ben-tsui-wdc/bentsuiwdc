# -*- coding: utf-8 -*-
""" Test case to uninstall same app for multiple users on the same device at the same time
    https://jira.wdmv.wdc.com/browse/KAM-32536
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


class ConcurrentUninstallSameAppMultipleUsers(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32536 - Uninstall same app for multiple users on the same device at the same time'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32536'
    PRIORITY = 'Major'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.check_pm_list = False
        self.app_id = None

    def before_test(self):
        env_dict = self.env.dump_to_dict()
        env_dict.pop('_testcase')
        env_dict['Settings'] = ['serial_client=False']
        
        # For admin user import
        env_dict['app_id'] = self.app_id
        env_dict['check_pm_list'] = self.check_pm_list
        self.install_app = InstallApp(env_dict)
        self.uninstall_app = UninstallApp(env_dict)

        # For Second user import
        replace_username = self.env.username.rsplit('@')[0]
        username = self.env.username.replace(replace_username, replace_username + '+1')
        self.log.info("Second user email = '{}'".format(username))
        env_dict['username'] = username
        self.install_app1 = InstallApp(env_dict)
        self.uninstall_app1 = UninstallApp(env_dict)

    def test(self):
        self.log.info('Prepare to install app({0}) for admin user and second user first ...'.format(self.app_id))
        self.install_app.test()
        self.install_app1.test()
        self.log.info('Start to uninstall app({0}) by admin user and second user at the same time'
            .format(self.app_id))
        self.concurrent_uninstall_app()
        self.log.info("*** Uninstall same app for multiple users on the same device at the same time, Test PASSED !!!")

    def concurrent_uninstall_app(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        mte.append_thread_by_func(target=self.uninstall_app.test)
        mte.append_thread_by_func(target=self.uninstall_app1.test)
        mte.run_threads()

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Un-install same app for multiple users on the same device at the same time test ***
        Examples: ./start.sh app_manager_scripts/concur_uninstall_same_app_multiple_users.py -ip 10.92.234.16 -env qa1
        --app_id com.wdc.importapp.ibi
        """)

    parser.add_argument('-appid', '--app_id', help='First App ID to installed')
    parser.add_argument('-chkpl', '--check_pm_list', help='Check pm list of app package', action='store_true')
    
    test = ConcurrentUninstallSameAppMultipleUsers(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)