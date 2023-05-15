# -*- coding: utf-8 -*-
""" Test case to uninstall app to test app manager.
    https://jira.wdmv.wdc.com/browse/KAM-32248
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import os
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class UninstallApp(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32248 - Uninstall App'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32248'
    PRIORITY = 'Critical'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.check_pm_list = False

    def init(self):
        self.upload_sqlite3()

    def before_test(self):
        pm_list_check = self.adb.executeShellCommand('pm list package | grep {}'.format(self.app_id))
        if not pm_list_check[0]:
            raise self.err.TestSkipped('There are no App({0}) installed ! Skipped the Uninstall App test !'.format(self.app_id))

    def test(self):
        self.uninstall_app()
        self.get_app_logcat_logs()
        self.uninstall_app_pass_criteria_check()
        self.check_appmgr_db_uninstall()
        self.log.info('App({}) has been uninstalled. Test PASSED !!!'.format(self.app_id))

    def uninstall_app(self):
        response = self.uut_owner.uninstall_app(self.app_id, retry_times=0)
        if response == 404:
            raise self.err.TestSkipped('There are no App({0}) installed ! Skipped the Uninstall App test !'.format(self.app_id))
        elif response < 500:
            self.log.info('Wait 10 secs for app manager to handle some retry mechanism if needed. App({0})'.format(self.app_id))
            time.sleep(10)
        else:
            self.log.warning('Response code {0} happened, sent uninstall request again ...'.format(response))
            response = self.uut_owner.uninstall_app(self.app_id, retry_times=2)
            self.log.warning('Response code: {}'.format(response))
            if response < 500:
                self.log.warning('Wait more 10 secs to let app manager handle retry mechanism')
                time.sleep(10)

    def get_app_logcat_logs(self, user_id_only=False, appmanager_only=False, app_id_only=False):
        if user_id_only:
            self.log.warning('Check appmgr logcat logs with grep user_id only ...')
            self.logcat_check = self.adb.executeShellCommand("logcat -d -s appmgr | grep '{}'".format(self.uut_owner.get_user_id()))[0]
        elif app_id_only:
            self.log.warning('Check appmgr logcat logs with grep app_id only ...')
            self.logcat_check = self.adb.executeShellCommand("logcat -d -s appmgr | grep '{}'".format(self.app_id))[0]
        elif appmanager_only:
            self.log.warning('Check for all appmgr logcat logs ...')
            self.logcat_check = self.adb.executeShellCommand("logcat -d -s appmgr")[0]  
        else:
            self.logcat_check = self.adb.executeShellCommand("logcat -d -s appmgr | grep {0} | grep '{1}'"
                .format(self.app_id, self.uut_owner.get_user_id()))[0]

    def uninstall_app_pass_criteria_check(self):
        check_list = ['app-uninstall-request', 'delete-app-user-success', 'app-uninstall-success']
        if 'delete-app-user-failed' in self.logcat_check:
            if 'Failed to bind unmount, trying again' in self.logcat_check:
                self.log.warning('Device or resource busy, Failed to bind unmount, trying again happened on App({}), '
                    'skip the delete-app-user-failed check ...'.format(self.app_id))
            else:
                raise self.err.TestFailure('delete-app-user-failed found when uninstall App({}), Test Failed !!!'.format(self.app_id))
        if 'app-uninstall-failed' in self.logcat_check:
            self.log.warning("'app-uninstall-failed' found in logcat, start the logic check to confirm the failure reason ...")
            self.get_app_logcat_logs(app_id_only=True)
            if 'App not installed' in self.logcat_check:
                self.log.warning('There may got 504 timeout when send uninstall request on App({}), '
                    'skip the app-uninstall-failed check ...'.format(self.app_id))
            elif 'app-uninstall-error' in self.logcat_check:
                self.log.warning("'app-uninstall-error' found, check 'request canceled' or 'EOF' message or '502' response "
                    "(For IBIX-3777, IBIX-4343 workaround)")
                self.get_app_logcat_logs(appmanager_only=True)
                if 'request canceled' in self.logcat_check or 'EOF' in self.logcat_check:
                    self.log.warning('request canceled or EOF found, skip the app-uninstall-error check and will resent uninstall request again ...')
                    self.adb.clean_logcat()
                    self.uninstall_app()
                    self.get_app_logcat_logs()
                    self.uninstall_app_pass_criteria_check()
                elif '502' in self.logcat_check:
                    self.log.warning('cloud return 502 found, '
                        'skip the app-uninstall-error check and do not resent uninstall request due to 5xx handle mehchanism ...')
                else:
                    raise self.err.TestFailure('app-uninstall-error found when uninstall App({}), Test Failed !!!'.format(self.app_id))
            else:
                raise self.err.TestFailure('app-uninstall-failed found when uninstall App({}), Test Failed !!!'.format(self.app_id))
        if not all(word in self.logcat_check for word in check_list):
            self.get_app_logcat_logs(user_id_only=True)
            if not all(word in self.logcat_check for word in check_list):
                raise self.err.TestFailure('Some check items is not in the check list, App({}) ! Test Failed !!!'.format(self.app_id))
        if self.check_pm_list:
            pm_list_check = self.adb.executeShellCommand('pm list package | grep {}'.format(self.app_id))
            if pm_list_check[0]:
                raise self.err.TestFailure('{} App still in the pm list ! Test Failed !!!'.format(self.app_id))

    def upload_sqlite3(self):
        self.log.info('Upload sqlite3 to the device ...')
        self.adb.executeShellCommand("mount -o remount,rw /system")
        self.adb.push(local='app_manager_scripts/sqlite3', remote='/system/bin')

    def check_appmgr_db_uninstall(self):
        self.log.info('Start to check app manager database info ...')
        userID = self.uut_owner.get_user_id()
        db = self.adb.executeShellCommand("sqlite3 /data/wd/appmgr/db/index.db .dump | grep {0} | grep '{1}'"
            .format(self.app_id, userID))[0]
        while 'Text file busy' in db:
            db = self.adb.executeShellCommand("sqlite3 /data/wd/appmgr/db/index.db .dump | grep {0} | grep '{1}'"
                .format(self.app_id, userID))[0]
            time.sleep(1)
        if db:
            raise self.err.TestFailure('The userID({0}) with appID({1}) is in database, test Failed !!!'
                .format(userID, self.app_id))


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Uninstall App Test Script ***
        Examples: ./run.sh app_manager_scripts/uninstall_app.py --uut_ip 10.92.224.68\
        """)

    parser.add_argument('-appid', '--app_id', help='App ID to uninstalled')
    parser.add_argument('-chkpl', '--check_pm_list', help='Check pm list of app package', action='store_true')

    test = UninstallApp(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
