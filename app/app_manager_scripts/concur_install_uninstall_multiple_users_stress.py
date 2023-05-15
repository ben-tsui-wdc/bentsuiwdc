# -*- coding: utf-8 -*-
""" Test case to loop and concurrent install and uninstall the same app with multiple users case
    https://jira.wdmv.wdc.com/browse/KAM-33048
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
# from platform_libraries.restAPI import RestAPI
from platform_libraries.test_thread import MultipleThreadExecutor


class ConcurrentInstallUninstallAppStressMultipleUsers(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'Concurrent Install and Uninstall same app with multiple user stress test'
    REPORT_NAME = 'Stress'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-33048'
    PRIORITY = 'Critical'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.number_of_users = 2
        self.interval_time = 15
        self.install_only = False
        self.uninstall_only = False
        self.check_app_install = False

    def before_loop(self):
        self.TEST_FAILED = False
        self.number_of_users = int(self.number_of_users)
        env_dict = self.env.dump_to_dict()
        env_dict.pop('_testcase')
        env_dict['Settings'] = ['serial_client=False']
        for idx in range(1, self.number_of_users+1):
            replace_username = self.env.username.rsplit('@')[0]
            username = self.env.username.replace(replace_username, replace_username + '+' + str(idx))
            self.log.info("user{0} email = '{1}'".format(idx, username))
            env_dict['username'] = username
            env_dict['app_id'] = self.app_id
            env_dict['apk_file_name'] = self.apk_file_name
            env_dict['apk_file_url'] = self.apk_file_url
            env_dict['delete_apk_file'] = self.delete_apk_file
            env_dict['check_app_install'] = self.check_app_install
            if not self.uninstall_only:
                setattr(self, 'install_app{}'.format(idx), InstallApp(env_dict))
                getattr(self, 'install_app{}'.format(idx)).before_test()
            if not self.install_only: 
                setattr(self, 'uninstall_app{}'.format(idx), UninstallApp(env_dict))

    def test(self):
        try:
            if self.install_only:
                self.log.info('Only install app with {} multiple users'.format(self.number_of_users))
                self.test_concurrent_install()
                test_result = 'Passed'
            elif self.uninstall_only:
                self.log.info('Only uninstall app with {} multiple users'.format(self.number_of_users))
                self.test_concurrent_uninstall()
                test_result = 'Passed'
            else:
                self.test_concurrent_install()
                # Wait for loadtest app to run for a while
                self.log.info('Interval time between Multiple users Install and Unstall App, sleep {} secs ... '.format(self.interval_time))
                time.sleep(int(self.interval_time))
                self.test_concurrent_uninstall()
                test_result = 'Passed'
        except Exception as ex:
            self.log.error('Concurrent install&uninstall app with multiple users failed! Error message: {}'.format(repr(ex)))
            test_result = 'Failed'
            self.TEST_FAILED = True
            raise
        self.log.info("*** Concurrent Install & Uninstall Same App with multiple users, Test Result: {} ***".format(test_result))
        self.data.test_result['ConcurrentInstallUninstallAppResultMultipleUsers'] = test_result

    def test_concurrent_install(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        for idx in range(1, self.number_of_users+1):
            mte.append_thread_by_func(target=getattr(self, 'install_app{}'.format(idx)).test)
        mte.run_threads()

    def test_concurrent_uninstall(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        for idx in range(1, self.number_of_users+1):
            mte.append_thread_by_func(target=getattr(self, 'uninstall_app{}'.format(idx)).test)
        mte.run_threads()

    def after_loop(self):
        for idx in range(1, self.number_of_users+1):
            if not self.uninstall_only:
                getattr(self, 'install_app{}'.format(idx)).after_test()
        if self.TEST_FAILED:
            raise self.err.TestFailure('At least 1 of the iterations failed!')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Concurrent Install&Uninstall App stress test ***
        Examples: ./start.sh app_manager_scripts/concur_install_uninstall_multiple_users_stress.py -ip 10.92.234.16 -env qa1 \
                  --loop_times 10 --number_of_users 2 --app_id com.wdc.importapp.ibi --logstash http://10.92.234.101:8000 \
        """)

    parser.add_argument('-itime', '--interval_time', default=15, help='Interval time between Install and Uninstall app')
    parser.add_argument('-num_urs', '--number_of_users', default=2, help='The number of users want to excute install and Uninstall app')
    parser.add_argument('-appid', '--app_id', help='App ID to installed')
    parser.add_argument('-apkname', '--apk_file_name', help='App package file name')
    parser.add_argument('-apkurl', '--apk_file_url', help='App package file download URL')
    parser.add_argument('-dapk', '--delete_apk_file', help='Delete App package file in user folder', action='store_true')
    parser.add_argument('-chkapp', '--check_app_install', help='Remove app before start install app test', action='store_true')
    parser.add_argument('-install_o', '--install_only', help='only install the app with multiple users', action='store_true')
    parser.add_argument('-uninstall_o', '--uninstall_only', help='only uninstall the app with multiple users', action='store_true')
    
    test = ConcurrentInstallUninstallAppStressMultipleUsers(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)