# -*- coding: utf-8 -*-
""" Test case to Install app, reboot, check app is started.
    https://jira.wdmv.wdc.com/browse/KAM-32326
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from app_manager_scripts.install_app import InstallApp
from bat_scripts_new.reboot import Reboot


class InstallAppReboot(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32326 - Install App and Reboot Device'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32326'
    PRIORITY = 'Major'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.uninstall_app = False
        self.app_id = None
        self.apk_file_name = None
        self.apk_file_url = None
        self.delete_apk_file = False
        self.check_app_install = False

    def init(self):
        env_dict = self.env.dump_to_dict()
        env_dict['app_id'] = self.app_id
        env_dict['apk_file_name'] = self.apk_file_name
        env_dict['apk_file_url'] = self.apk_file_url
        env_dict['delete_apk_file'] = self.delete_apk_file
        env_dict['check_app_install'] = self.check_app_install
        env_dict['uninstall_app'] = self.uninstall_app
        self.install_app = InstallApp(env_dict)
        self.reboot = Reboot(env_dict)

    def test(self):
        # Install app
        self.install_app.before_test()
        self.install_app.test()
        # Reboot device
        self.reboot.wait_device = True
        self.reboot.no_rest_api = True
        self.reboot.disable_ota = False
        self.reboot.test()
        self.log.info('Wait 3 mins to let app update check finished')
        time.sleep(60*3)
        # Check logs and pm list
        pm_list_check = self.adb.executeShellCommand('pm list package | grep {}'.format(self.install_app.app_id))
        logcat_check = self.adb.executeShellCommand('logcat -d -s appmgr | grep {}'.format(self.install_app.app_id))[0]
        check_list = ['check-app-updates', 'App found', 'check-all-app-updates"', 'User for app found']
        if not pm_list_check[0]:
            raise self.err.TestFailure('APP({}) is not launch successfully, test Failed !!!'.format(self.install_app.app_id))
        if not all(word in logcat_check for word in check_list):
            self.log.warning('Wait 1 more min to let app update check finished ...')
            time.sleep(60)
            logcat_check = self.adb.executeShellCommand('logcat -d -s appmgr | grep {}'.format(self.install_app.app_id))[0]
            if not all(word in logcat_check for word in check_list):
                raise self.err.TestFailure('APP({}) is not launch successfully, test Failed !!!'.format(self.install_app.app_id))
        self.install_app.check_appmgr_db_install()
        self.log.info('App({}) has been launched. Test PASSED !!!'.format(self.install_app.app_id))

    def after_test(self):
        # Remove apk file or uninstall app if needed
        self.install_app.after_test()


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Install App and Reboot Test Script ***
        Examples: ./run.sh app_manager_scripts/install_app_reboot.py --uut_ip 10.92.224.68 --uninstall_app\
        """)

    parser.add_argument('-uninstall_app', '--uninstall_app', help='Uninstall installed app after test', action='store_true')
    parser.add_argument('-appid', '--app_id', help='App ID to installed')
    parser.add_argument('-apkname', '--apk_file_name', help='App package file name')
    parser.add_argument('-apkurl', '--apk_file_url', help='App package file download URL')
    parser.add_argument('-dapk', '--delete_apk_file', help='Delete App package file in user folder', action='store_true')
    parser.add_argument('-chkapp', '--check_app_install', help='Remove app before start install app test', action='store_true')

    test = InstallAppReboot(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
