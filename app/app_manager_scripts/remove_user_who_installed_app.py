# -*- coding: utf-8 -*-
""" Test case to test remove member who has installed app from device
    https://jira.wdmv.wdc.com/browse/KAM-32535
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from app_manager_scripts.install_app import InstallApp
from platform_libraries.test_thread import MultipleThreadExecutor


class RemoveUserWhoInstalledApp(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32535 - Remove member who has installed app from device'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32535'
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

        # For Second user import
        replace_username = self.env.username.rsplit('@')[0]
        self.second_user = self.env.username.replace(replace_username, replace_username + '+1')
        self.log.info("Second user email = '{}'".format(self.second_user))
        env_dict['username'] = self.second_user
        self.install_app = InstallApp(env_dict)
        # Sometimes got 403 Forbidden due to "Attempted actions is unauthorized" happened for second user, add waiting time for workaround
        time.sleep(3)
        self.log.info('Start to install app({0}) by second user({1}) ...'.format(self.app_id_1, self.second_user))
        self.install_app.app_id = self.app_id_1
        self.install_app.test()
        self.log.info('Start to install app({0}) by second user({1}) ...'.format(self.app_id_2, self.second_user))
        self.install_app.app_id = self.app_id_2
        self.install_app.test()

    def test(self):
        self.log.info('Start to remove memeber({}) and check app was uninstalled after user has been removed ...'.format(self.second_user))
        user_id = self.install_app.uut_owner.get_user_id()
        id_token = self.install_app.uut_owner.get_id_token()
        self.uut_owner.detach_user_from_device(user_id=user_id, id_token=id_token)
        self.log.info('User({0}|{1}) has been removed'.format(self.second_user, user_id))
        self.log.info('Wait 30 secs to let device to uninstall apps automatically ...')
        time.sleep(30)
        self.check_app_uninstalled(appid=self.app_id_1, userid=user_id)
        self.check_app_uninstalled(appid=self.app_id_2, userid=user_id)
        self.check_appmgr_db_uninstall(appid=self.app_id_1, userid=user_id)
        self.check_appmgr_db_uninstall(appid=self.app_id_2, userid=user_id)
        self.log.info("*** Remove member who has installed app from device, Test PASSED !!!")

    def check_app_uninstalled(self, appid, userid):
        logcat_check = self.adb.executeShellCommand("logcat -d -s appmgr | grep {0} | grep '{1}'"
            .format(appid, userid))[0]
        check_list = ['app-uninstall-request', 'delete-app-user-success', 'app-uninstall-success', 'uninstall-for-user-debug']
        if self.check_pm_list:
            pm_list_check = self.adb.executeShellCommand('pm list package | grep {}'.format(appid))
            if pm_list_check[0]:
                raise self.err.TestFailure('{} App still in the pm list ! Test Failed !!!'.format(appid))
        if not all(word in logcat_check for word in check_list):
            self.log.warning('Check appmgr logcat logs with grep user_id only ...')
            logcat_check_user_id = self.adb.executeShellCommand("logcat -d -s appmgr | grep '{}'".format(userid))[0]
            if not all(word in logcat_check_user_id for word in check_list):
                raise self.err.TestFailure('Some check items is not in the check list, App({}) ! Test Failed !!!'.format(appid))
        if 'delete-app-user-failed' in logcat_check:
            if 'Failed to bind unmount, trying again' in logcat_check:
                self.log.warning('Device or resource busy, Failed to bind unmount, trying again happened on App({}), '
                    'skip the delete-app-user-failed check ...'.format(appid))
        if 'app-uninstall-failed' in logcat_check:
            if 'App not installed' in logcat_check:
                self.log.warning('There may got 504 timeout when send uninstall request on App({}), '
                    'skip the app-uninstall-failed check ...'.format(appid))
            else:
                raise self.err.TestFailure('app-uninstall-failed found when uninstall App({}), Test Failed !!!'.format(appid))
        self.log.info('App({}) has been uninstalled !!!'.format(appid))

    def check_appmgr_db_uninstall(self, appid, userid):
        self.log.info('Start to check app manager database info ...')
        self.adb.executeShellCommand("mount -o remount,rw /system")
        self.adb.push(local='app_manager_scripts/sqlite3', remote='/system/bin')
        db = self.adb.executeShellCommand("sqlite3 /data/wd/appmgr/db/index.db .dump | grep {0} | grep '{1}'"
            .format(appid, userid))[0]
        while 'Text file busy' in db:
            db = self.adb.executeShellCommand("sqlite3 /data/wd/appmgr/db/index.db .dump | grep {0} | grep '{1}'"
                .format(self.app_id, userID))[0]
            time.sleep(1)
        if db:
            raise self.err.TestFailure('The userID({0}) with appID({1}) is not in database, test Failed !!!'
                .format(userid, appid))


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Remove member who has installed app from device test ***
        Examples: ./start.sh app_manager_scripts/remove_user_who_installed_app.py -ip 10.92.234.16 -env qa1
        --app_id_1 com.wdc.importapp.ibi --app_id_2 com.elephantdrive.ibi
        """)

    parser.add_argument('-appid1', '--app_id_1', help='First App ID to installed', required=True)
    parser.add_argument('-appid2', '--app_id_2', help='Second App ID to installed', required=True)
    parser.add_argument('-chkpl', '--check_pm_list', help='Check pm list of app package', action='store_true')
    
    test = RemoveUserWhoInstalledApp(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)