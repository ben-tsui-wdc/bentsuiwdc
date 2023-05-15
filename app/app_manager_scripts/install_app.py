# -*- coding: utf-8 -*-
""" Test case to install app to test app manager.
    https://jira.wdmv.wdc.com/browse/KAM-32247
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import os
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class InstallApp(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32247 - Install App'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32247'
    PRIORITY = 'Critical'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.appURL = None
        self.uninstall_app = False
        self.app_id = None
        self.apk_file_name = None
        self.apk_file_url = None
        self.delete_apk_file = False
        self.check_app_install = False

    def init(self):
        self.timeout = 60*15
        self.upload_sqlite3()
        if self.apk_file_url:
            self.apk_file_name = self.apk_file_url.rsplit('/', 1).pop()
        self.log.info('APK name: {}'.format(self.apk_file_name))
        if self.apk_file_name:
            self.appURL = 'file://{}'.format(self.apk_file_name)
        self.log.info('App URL: {}'.format(self.appURL))

    def before_test(self):
        if self.check_app_install:
            pm_list_check = self.adb.executeShellCommand('pm list packages | grep {}'.format(self.app_id))
            if pm_list_check[0]:
                self.log.warning('The APP({}) already installed, start to remove the app before test ...'.format(self.app_id))
                self.uut_owner.uninstall_app(self.app_id, retry_times=0)
            time.sleep(1)
        if self.apk_file_url:
            self.log.info('Start to download apk file from path({})'.format(self.apk_file_url))
            self.adb.executeCommand(cmd='wget -q "{}" -O {}'.format(self.apk_file_url, self.apk_file_name), consoleOutput=True, timeout=60*5)
            self.log.info('Start to upload apk file({0}) to user({1}) folder...'.format(self.apk_file_name, self.uut_owner.get_user_id()))
            with open(self.apk_file_name, 'rb') as f:
                self.uut_owner.chuck_upload_file(file_object=f, file_name=self.apk_file_name)
            self.log.info('Upload apk file({}) success ...'.format(self.apk_file_name))

    def test(self):
        self.install_app(retry_times=0)
        self.check_app_status()
        self.get_pm_list_and_app_logcat_logs()
        check_list = ['connection reset by peer', 'Failed to update the app catalog about app installation']
        if any(word in self.logcat_check for word in check_list):
            if 'connection reset by peer' in self.logcat_check:
                self.log.warning("'connection reset by peer' happened, try to install app again ...")
            if 'Failed to update the app catalog about app installation' in self.logcat_check:
                self.log.warning("'Failed to update the app catalog about app installation, so deleting the app' happened, try to install app again ...")
            self.install_app(retry_times=3)
            self.check_app_status()
            self.get_pm_list_and_app_logcat_logs()
        self.pass_criteria_check()
        self.check_appmgr_db_install()
        self.log.info('App({}) has been installed. Test PASSED !!!'.format(self.app_id))

    def install_app(self, retry_times=0):
        self.timing.start()
        while not self.timing.is_timeout(self.timeout):
            successCode = self.uut_owner.install_app(app_id=self.app_id, app_url=self.appURL, retry_times=retry_times)
            if successCode == 204:
                break
            elif successCode == 409:
                self.log.warning('return code {}, send install app request again ...'.format(successCode))
            else:
                self.log.error('Install request response: {}, stop to send request ...'.format(successCode))
                break
            time.sleep(5)

    def check_app_status(self):
        self.log.info('Check app installing status ...')
        self.timing.reset_start_time()
        while not self.timing.is_timeout(self.timeout):
            successCode = self.uut_owner.get_install_app_status(self.app_id)
            if successCode == 200 or successCode == 404:
                break
            time.sleep(5)
            self.log.info('Waiting for installation: {}'.format(successCode))
            if self.timing.is_timeout(self.timeout):
                self.log.error('Timeout for waiting app({}) installation'.format(self.app_id))

    def get_pm_list_and_app_logcat_logs(self):
        # Check app installed
        self.pm_list_check = self.adb.executeShellCommand('pm list package | grep {}'.format(self.app_id))
        if self.pm_list_check[0]:
            # Wait for app launch
            self.log.info('App({}) is in the pm list, wait 10 secs for app launched ...'.format(self.app_id))
            time.sleep(10)
            self.logcat_check = self.adb.executeShellCommand("logcat -d -s appmgr | grep {0}".format(self.app_id))[0]
        else:
            self.log.warning('App({}) is not in the pm list !'.format(self.app_id))
            self.logcat_check = self.adb.executeShellCommand("logcat -d -s appmgr | grep {0}".format(self.app_id))[0]

    def pass_criteria_check(self):
        check_list1 = ['app-install-success', 'app-install-request']
        if not self.pm_list_check[0] or not all(word in self.logcat_check for word in check_list1):
            raise self.err.TestFailure('APP({}) is not install successfully, test Failed !!!'.format(self.app_id))
        if 'app-install-failed' in self.logcat_check or 'download-and-install-failed' in self.logcat_check:
            if 'App installation in progress' in self.logcat_check:
                self.log.warning('There may have more than one user installation with the APP({}) running in parallel, '
                    'skip the app-install-failed check ...'.format(self.app_id))
            elif 'connection reset by peer' in self.logcat_check:
                self.log.error('connection reset by peer happened and retry installion 3 times if needed, '
                    'skip the app-install-failed or download-and-install-failed check ...')
            elif 'Failed to update the app catalog about app installation, so deleting the app' in self.logcat_check:
                self.log.warning('Failed to update the app catalog about app installation, the app has been deleted by app manager, '
                    'skip the download-and-install-failed check ...')
                if '502' in self.logcat_check: # cloud service 502 response
                    self.log.error('cloud return 502 found ...')
                elif 'EOF' in self.logcat_check:
                    self.log.error('cloud EOF happened ...')
            else:
                raise self.err.TestFailure('APP({}) is not install successfully, test Failed !!!'.format(self.app_id))
        # Launch app check
        self.timing.reset_start_time()
        while not self.timing.is_timeout(60*3):
            check_launch_app = self.adb.executeShellCommand('ps | grep {}'.format(self.app_id))[0]
            if check_launch_app:
                break
            self.log.warning('APP({}) not found in ps list, wait 10 secs and check again ...'.format(self.app_id))
            time.sleep(10)
            if self.timing.is_timeout(60*3):
                raise self.err.TestFailure('APP({}) is not launched successfully, test Failed !!!'.format(self.app_id))

    def upload_sqlite3(self):
        self.log.info('Upload sqlite3 to the device ...')
        self.adb.executeShellCommand("mount -o remount,rw /system")
        self.adb.push(local='app_manager_scripts/sqlite3', remote='/system/bin')

    def check_appmgr_db_install(self):
        self.log.info('Start to check app manager database info ...')
        userID = self.uut_owner.get_user_id()
        db = self.adb.executeShellCommand("sqlite3 /data/wd/appmgr/db/index.db .dump | grep {0} | grep '{1}'"
            .format(self.app_id, userID))[0]
        while 'Text file busy' in db:
            db = self.adb.executeShellCommand("sqlite3 /data/wd/appmgr/db/index.db .dump | grep {0} | grep '{1}'"
                .format(self.app_id, userID))[0]
            time.sleep(1)
        count = 1
        while not db:
            self.log.warning('Not found userID({0}) with appID({1}) in appmgr database, wait for 5 secs and get again, try {2} times ...'
                .format(userID, self.app_id, count))
            time.sleep(5)
            db = self.adb.executeShellCommand("sqlite3 /data/wd/appmgr/db/index.db .dump | grep {0} | grep '{1}'"
                .format(self.app_id, userID))[0]
            count += 1
            if count == 5:
                raise self.err.TestFailure('The userID({0}) with appID({1}) is not in database, test Failed !!!'
                    .format(userID, self.app_id))

    def after_test(self):
        if self.uninstall_app:
            self.log.info('Start to Uninstall App({}) ...'.format(self.app_id))
            self.uut_owner.uninstall_app(self.app_id, retry_times=3)
        if self.apk_file_name and self.delete_apk_file:
            self.log.info('Delete apk file({}) in userRoot folder'.format(self.apk_file_name))
            self.uut_owner.delete_file_by_name(name=self.apk_file_name)


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Install App Test Script ***
        Examples: ./run.sh app_manager_scripts/install_app.py --uut_ip 10.92.224.68 --uninstall_app\
        """)

    parser.add_argument('-appid', '--app_id', help='App ID to installed')
    parser.add_argument('-apkname', '--apk_file_name', help='App package file name')
    parser.add_argument('-apkurl', '--apk_file_url', help='App package file download URL')
    parser.add_argument('-dapk', '--delete_apk_file', help='Delete App package file in user folder', action='store_true')
    parser.add_argument('-chkapp', '--check_app_install', help='Remove app before start install app test', action='store_true')
    parser.add_argument('-uninstall_app', '--uninstall_app', help='Uninstall installed app after test', action='store_true')

    test = InstallApp(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
