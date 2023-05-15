# -*- coding: utf-8 -*-
""" Test case to loop and concurrent install and uninstall multiple apps to test app manager.
    https://jira.wdmv.wdc.com/browse/KAM-33047
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time
import threading

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from app_manager_scripts.install_app import InstallApp
from app_manager_scripts.uninstall_app import UninstallApp
from platform_libraries.test_thread import MultipleThreadExecutor


class ConcurrentInstallUninstallAppStressSingleUser(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'Concurrent Install and Uninstall multiple apps for admin user stress test'
    REPORT_NAME = 'Stress'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-33047'
    PRIORITY = 'Critical'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.number_of_app = 1
        self.interval_time = 15
        self.install_only = False
        self.uninstall_only = False

    def before_loop(self):
        self.TEST_FAILED = False
        self.number_of_app = int(self.number_of_app)
        env_dict = self.env.dump_to_dict()
        for idx in range(1, self.number_of_app+1):
            env_dict['apk_file_url'] = 'http://fileserver.hgst.com/test/app_manager/com.wdc.mycloud.loadtest.app{}.apk'.format(idx)
            env_dict['app_id'] = 'com.wdc.mycloud.loadtest.app{}'.format(idx)
            env_dict['delete_apk_file'] = True
            env_dict['check_pm_list'] = True
            env_dict['check_app_install'] = self.check_app_install
            if not self.uninstall_only:
                setattr(self, 'install_app{}'.format(idx), InstallApp(env_dict))
                getattr(self, 'install_app{}'.format(idx)).before_test()
            if not self.install_only:
                setattr(self, 'uninstall_app{}'.format(idx), UninstallApp(env_dict))

    def test(self):
        try:
            if self.install_only:
                self.log.info('Only install {} apps with single admin user'.format(self.number_of_app))
                self.test_concurrent_install()
                test_result = 'Passed'
            elif self.uninstall_only:
                self.log.info('Only uninstall {} apps with single admin user'.format(self.number_of_app))
                self.test_concurrent_uninstall()
                test_result = 'Passed'
            else:
                self.test_concurrent_install()
                # Wait for loadtest app to run for a while
                self.log.info('Interval time between Multiple Install and Unstall App, sleep {} secs ... '.format(self.interval_time))
                time.sleep(int(self.interval_time))
                self.test_concurrent_uninstall()
                test_result = 'Passed'
        except Exception as ex:
            self.log.error('Concurrent install&uninstall app failed! Error message: {}'.format(repr(ex)))
            test_result = 'Failed'
            self.TEST_FAILED = True
            raise
        self.log.info("*** Concurrent with multiple Install & Uninstall App Test Result: {} ***".format(test_result))
        self.data.test_result['ConcurrentInstallUninstallAppResultSingleUser'] = test_result

    def test_concurrent_install(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        for idx in range(1, self.number_of_app+1):
            mte.append_thread_by_func(target=getattr(self, 'install_app{}'.format(idx)).test)
        mte.run_threads()

    def test_concurrent_uninstall(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        for idx in range(1, self.number_of_app+1):
            mte.append_thread_by_func(target=getattr(self, 'uninstall_app{}'.format(idx)).test)
        mte.run_threads()

    def after_loop(self):
        for idx in range(1, self.number_of_app+1):
            if not self.uninstall_only:
                getattr(self, 'install_app{}'.format(idx)).after_test()
        if self.TEST_FAILED:
            raise self.err.TestFailure('At least 1 of the iterations failed!')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Concurrent Install&Uninstall App stress test ***
        Examples: ./start.sh app_manager_scripts/concur_install_uninstall_single_user_stress.py -ip 10.92.234.16 -env qa1 \
                  --loop_times 10 --number_of_app 2 --logstash http://10.92.234.101:8000 \
        """)

    parser.add_argument('-itime', '--interval_time', default=15, help='Interval time between Install and Uninstall app')
    parser.add_argument('-numapp', '--number_of_app', help='The number of Loadtest Apps want to install')
    parser.add_argument('-chkapp', '--check_app_install', help='Remove app before start install app test', action='store_true')
    parser.add_argument('-install_o', '--install_only', help='only install the app with multiple users', action='store_true')
    parser.add_argument('-uninstall_o', '--uninstall_only', help='only uninstall the app with multiple users', action='store_true')
    
    test = ConcurrentInstallUninstallAppStressSingleUser(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)