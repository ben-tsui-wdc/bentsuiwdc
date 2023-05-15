# -*- coding: utf-8 -*-
""" Test case to reboot system during installation.
    https://jira.wdmv.wdc.com/browse/KAM-32650
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
from platform_libraries.test_thread import MultipleThreadExecutor


class RebootSystemDuringInstallApp(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32650 - Reboot system during installation'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32650'
    PRIORITY = 'Major'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.app_id = None
        self.check_app_install = False
        self.uninstall_app = False

    def init(self):
        env_dict = self.env.dump_to_dict()
        env_dict['app_id'] = self.app_id
        env_dict['check_app_install'] = self.check_app_install
        env_dict['uninstall_app'] = self.uninstall_app
        self.install_app = InstallApp(env_dict)
        self.install_app.before_test()
        self.reboot = Reboot(env_dict)

    def test(self):
        self.concurrent_reboot_install_app()
        self.install_app.timeout = 10
        self.install_app.check_app_status()
        self.log.info('Wait 3 mins to let app update check finished')
        time.sleep(60*3)
        self.install_app.get_pm_list_and_app_logcat_logs()
        if 'Deleted app with port 0' in self.install_app.logcat_check:
            self.log.warning('Deleted app with port 0 found! The app has been deleted because app '
                'installation has been interrupted during reboot.')
            self.log.warning('Start to install_app again ...')
            self.install_app.install_app()
            self.install_app.timeout = 60*15
            self.install_app.check_app_status()
            self.install_app.get_pm_list_and_app_logcat_logs()
        elif 'app-get-success' not in self.install_app.logcat_check:
            self.log.info('App not install before reboot, only check App record is not in the database ...')
            self.check_appmgr_db_uninstall()
            self.log.info('App record not in the database, Test PASSED !!!')
            return
        self.pass_criteria_check()
        self.install_app.check_appmgr_db_install()
        self.log.info('App({}) has been installed. Test PASSED !!!'.format(self.app_id))

    def pass_criteria_check(self):
        # Note: Didn't check app-install-request and app-install-success due to install request is sent before reboot
        #       and there is chance the installation was finished before the device reboots.
        if not self.install_app.pm_list_check[0]:
            raise self.err.TestFailure('APP({}) is not install successfully, test Failed !!!'.format(self.app_id))
        if 'app-install-failed' in self.install_app.logcat_check:
            if 'App installation in progress' in self.install_app.logcat_check:
                self.log.warning('There may have more than one user installation with the APP({}) running in parallel, '
                    'skip the app-install-failed check ...'.format(self.app_id))
            else:
                raise self.err.TestFailure('APP({}) is not install successfully, test Failed !!!'.format(self.app_id))
        check_app_user = self.adb.executeShellCommand("logcat -d -s appmgr | grep 'Check AppUser successfully'")[0]
        if not check_app_user:
            raise self.err.TestFailure("'Check AppUser successfully not found after device reboot, test Failed !!!")
        # Launch app check
        check_launch_app = self.adb.executeShellCommand('ps | grep {}'.format(self.app_id))[0]
        if not check_launch_app:
            raise self.err.TestFailure('APP({}) is not launched successfully, test Failed !!!'.format(self.app_id))

    def install_app_only(self):
        self.uut_owner.install_app(app_id=self.app_id)

    def reboot_device(self):
        self.reboot.wait_device = True
        self.reboot.no_rest_api = True
        self.reboot.disable_ota = False
        self.reboot.test()

    def concurrent_reboot_install_app(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        mte.append_thread_by_func(target=self.install_app_only)
        mte.append_thread_by_func(target=self.reboot_device)
        mte.run_threads()

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

    def after_test(self):
        self.install_app.after_test()

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Reboot system during installation Test Script ***
        Examples: ./run.sh app_manager_scripts/concur_reboot_install_app.py --uut_ip 10.92.224.68 -appid com.wdc.importapp.ibi -chkapp\
        """)

    parser.add_argument('-appid', '--app_id', help='App ID to installed')
    parser.add_argument('-chkapp', '--check_app_install', help='Remove app before start install app test', action='store_true')
    parser.add_argument('-uninstall_app', '--uninstall_app', help='Uninstall installed app after test', action='store_true')

    test = RebootSystemDuringInstallApp(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
