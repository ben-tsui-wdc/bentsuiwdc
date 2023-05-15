# -*- coding: utf-8 -*-
""" Test case to Install multiple apps at the same time for the admin user
    https://jira.wdmv.wdc.com/browse/KAM-32324
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from app_manager_scripts.install_app import InstallApp
from platform_libraries.test_thread import MultipleThreadExecutor


class ConcurrentInstallMultipleAppAdminUser(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32324 - Install multiple apps at the same time for the admin user'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32324'
    PRIORITY = 'Major'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.check_app_install = False
        self.app_id_1 = None
        self.app_id_2 = None
        self.app_id_3 = None

    def before_test(self):
        env_dict = self.env.dump_to_dict()
        env_dict['check_app_install'] = self.check_app_install

        # New object for different apps install
        env_dict['app_id'] = self.app_id_1
        self.install_app1 = InstallApp(env_dict)
        self.install_app1.before_test()
        env_dict['app_id'] = self.app_id_2
        self.install_app2 = InstallApp(env_dict)
        self.install_app2.before_test()
        if self.app_id_3:
            env_dict['app_id'] = self.app_id_3
            self.install_app3 = InstallApp(env_dict)
            self.install_app3.before_test()

    def test(self):
        self.log.info('Start to install multiple apps by admin user at the same time ...')
        self.concurrent_install_app()
        self.log.info("*** Install multiple apps at the same time for the admin user, Test PASSED !!!")

    def concurrent_install_app(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        mte.append_thread_by_func(target=self.install_app1.test)
        mte.append_thread_by_func(target=self.install_app2.test)
        if self.app_id_3:
            mte.append_thread_by_func(target=self.install_app3.test)
        mte.run_threads()

    def after_test(self):
        self.install_app1.uninstall_app = True
        self.install_app1.after_test()
        self.install_app2.uninstall_app = True
        self.install_app2.after_test()
        if self.app_id_3:
            self.install_app3.uninstall_app = True
            self.install_app3.after_test()

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Install multiple apps at the same time for the admin user test ***
        Examples: ./start.sh app_manager_scripts/concur_install_multiple_apps_admin_user.py -ip 10.92.234.16 -env qa1
        --app_id_1 com.wdc.importapp.ibi --app_id_2 com.elephantdrive.ibi --app_id_3 com.wdc.mycloud.loadtest.app1
        """)

    parser.add_argument('-appid1', '--app_id_1', help='First App ID to installed', required=True)
    parser.add_argument('-appid2', '--app_id_2', help='Second App ID to installed', required=True)
    parser.add_argument('-appid3', '--app_id_3', help='Third App ID to installed', required=False)
    parser.add_argument('-chkapp', '--check_app_install', help='Remove app before start install app test', action='store_true')
    
    test = ConcurrentInstallMultipleAppAdminUser(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)