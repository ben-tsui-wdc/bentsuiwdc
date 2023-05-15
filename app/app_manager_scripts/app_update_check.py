# -*- coding: utf-8 -*-
""" Test case to test app Update - Update app version from Cloud side.
    https://jira.wdmv.wdc.com/browse/KAM-33046
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time
import re

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.cloud_api import CloudAPI
from app_manager_scripts.install_app import InstallApp
from bat_scripts_new.reboot import Reboot


class AppUpdateCheck(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-33046 - App Update - Update app version from Cloud side'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-33046'
    PRIORITY = 'Major'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.uninstall_app = False

    def init(self):
        self.timeout = 60*5
        self.app_id = 'com.wdc.mycloud.loadtest.app1'
        env_dict = self.env.dump_to_dict()
        env_dict['app_id'] = self.app_id
        env_dict['uninstall_app'] = self.uninstall_app
        self.install_app = InstallApp(env_dict)
        self.cloud_obj = CloudAPI(env=self.env.cloud_env)

    def before_test(self):
        # Install app
        self.install_app.test()
        cur_app_version = self.adb.executeShellCommand("sqlite3 /data/wd/appmgr/db/index.db .dump | grep {0} | grep apps | grep VALUES"
            .format(self.app_id))[0]
        self.log.info('Current Installed App Version: {}'.format(re.findall(r'[(](.*?)[)]', cur_app_version)))

    def test(self):
        app_version = self.cloud_obj.get_latest_app_version_info(appId=self.app_id).get('version')
        self.log.info('Current App version is: {}'.format(app_version))
        cur_ver = app_version.split('.')[2]
        new_ver = int(cur_ver)+1
        new_app_version = '{0}.{1}.{2}'.format(app_version.split('.')[0], app_version.split('.')[1], new_ver)
        self.log.warning('Start to update App({0}) version to {1}'.format(self.app_id, new_app_version))
        self.cloud_obj.update_create_loadtestapp_app_record(version=new_app_version)
        time.sleep(1)
        app_version = self.cloud_obj.get_latest_app_version_info(appId=self.app_id).get('version')
        if app_version != new_app_version:
            raise self.err.TestSkipped('Update App record failed, TestSkipped !!!')
        else:
            self.log.info('Updated app version successfully. Version: {}'.format(app_version))
        self.log.info('Restarting appmgr service to trigger app manager check app update ...')
        self.adb.executeShellCommand('stop appmgr')
        self.adb.executeShellCommand('start appmgr')
        # Time wait for check app update execute
        self.log.info('Wait 2 mins for check app updates start ...')
        time.sleep(60*2)
        self.timing.start()
        while not self.timing.is_timeout(self.timeout):
            check_app_updates = self.adb.executeShellCommand('logcat -d -s appmgr | grep check-all-app-updates')[0]
            if check_app_updates:
                break
            self.log.warning('check-app-updates not found, wait for more 10 secs ...')
            time.sleep(10)
        self.timing.reset_start_time()
        while not self.timing.is_timeout(self.timeout):
            check_app_update_success = self.adb.executeShellCommand('logcat -d -s appmgr | grep {}'.format(self.app_id))[0]
            if 'App update successfully' in check_app_update_success:
                break
            self.log.warning("'App update successfully' not in logcat, wait for more 20 secs ...")
            time.sleep(20)
        cur_app_version = self.adb.executeShellCommand("sqlite3 /data/wd/appmgr/db/index.db .dump | grep {0} | grep apps | grep VALUES"
            .format(self.app_id))[0]
        self.log.info('Current Installed App Version: {}'.format(re.findall(r'[(](.*?)[)]', cur_app_version)))
        if new_app_version not in cur_app_version:
            raise self.err.TestFailure('App Update app version from Cloud side, test Failed !!!')
        self.log.info('App Update - Update app version from Cloud side, Test PASSED !!!')

    def after_test(self):
        self.install_app.after_test()


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** App Update Check Test Script ***
        Examples: ./run.sh app_manager_scripts/app_update_check.py --uut_ip 10.92.224.68 --uninstall_app\
        """)

    parser.add_argument('-uninstall_app', '--uninstall_app', help='Uninstall installed app after test', action='store_true')

    test = AppUpdateCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
