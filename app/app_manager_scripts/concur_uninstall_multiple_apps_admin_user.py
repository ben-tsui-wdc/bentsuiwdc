# -*- coding: utf-8 -*-
""" Test case to Un-install multiple apps at the same time for the admin user
    https://jira.wdmv.wdc.com/browse/KAM-32539
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


class ConcurrentUninstallMultipleAppAdminUser(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32539 - Uninstall multiple apps at the same time for the admin user'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32539'
    PRIORITY = 'Major'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.check_pm_list = False
        self.app_id_1 = None
        self.app_id_2 = None
        self.app_id_3 = None

    def before_test(self):
        env_dict = self.env.dump_to_dict()
        # For admin user import
        env_dict['check_pm_list'] = self.check_pm_list
        self.install_app = InstallApp(env_dict)

        # New object for different apps uninstall
        env_dict['app_id'] = self.app_id_1
        self.uninstall_app1 = UninstallApp(env_dict)
        env_dict['app_id'] = self.app_id_2
        self.uninstall_app2 = UninstallApp(env_dict)
        if self.app_id_3:
            env_dict['app_id'] = self.app_id_3
            self.uninstall_app3 = UninstallApp(env_dict)

    def test(self):
        self.log.info('Prepare to install multiple apps ...')
        self.install_app.app_id = self.app_id_1
        self.install_app.test()
        self.install_app.app_id = self.app_id_2
        self.install_app.test()
        if self.app_id_3:
            self.install_app.app_id = self.app_id_3
            self.install_app.test()
        self.log.info('Start to uninstall multiple apps by admin user at the same time ...')
        self.concurrent_uninstall_app()
        self.log.info("*** Uninstall multiple apps at the same time for the admin user, Test PASSED !!!")

    def concurrent_uninstall_app(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        mte.append_thread_by_func(target=self.uninstall_app1.test)
        mte.append_thread_by_func(target=self.uninstall_app2.test)
        if self.app_id_3:
            mte.append_thread_by_func(target=self.uninstall_app3.test)
        mte.run_threads()

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Uninstall multiple apps at the same time for the admin user test ***
        Examples: ./start.sh app_manager_scripts/concur_uninstall_multiple_apps_admin_user.py -ip 10.92.234.16 -env qa1
        --app_id_1 com.wdc.importapp.ibi --app_id_2 com.elephantdrive.ibi --app_id_3 com.wdc.mycloud.loadtest.app1
        """)

    parser.add_argument('-appid1', '--app_id_1', help='First App ID to installed', required=True)
    parser.add_argument('-appid2', '--app_id_2', help='Second App ID to installed', required=True)
    parser.add_argument('-appid3', '--app_id_3', help='Third App ID to installed', required=False)
    parser.add_argument('-chkpl', '--check_pm_list', help='Check pm list of app package', action='store_true')
    
    test = ConcurrentUninstallMultipleAppAdminUser(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)