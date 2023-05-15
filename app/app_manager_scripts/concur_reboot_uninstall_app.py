# -*- coding: utf-8 -*-
""" Test case to reboot system during uninstallation.
    https://jira.wdmv.wdc.com/browse/KAM-32651
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


class RebootSystemDuringUninstallApp(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32651 - Reboot system during uninstallation'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32651'
    PRIORITY = 'Major'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.app_id = None

    def init(self):
        env_dict = self.env.dump_to_dict()
        env_dict['app_id'] = self.app_id
        self.install_app = InstallApp(env_dict)
        self.reboot = Reboot(env_dict)
        # Install app
        self.install_app.test()

    def test(self):
        self.concurrent_reboot_uninstall_app()
        # Check logs and pm list
        pm_list_check = self.adb.executeShellCommand('pm list package | grep {}'.format(self.app_id))
        if pm_list_check[0]:
            raise self.err.TestFailure('App({}) still in the pm list ! Test Failed !!!'.format(self.app_id))
        self.check_appmgr_db_uninstall()
        self.log.info('App({}) has been uninstalled. Test PASSED !!!'.format(self.install_app.app_id))

    def uninstall_app(self):
        self.uut_owner.uninstall_app(self.app_id)

    def reboot_device(self):
        self.reboot.wait_device = True
        self.reboot.no_rest_api = True
        self.reboot.disable_ota = False
        self.reboot.test()

    def concurrent_reboot_uninstall_app(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        mte.append_thread_by_func(target=self.uninstall_app)
        mte.append_thread_by_func(target=self.reboot_device)
        mte.run_threads()

    def check_appmgr_db_uninstall(self):
        self.log.info('Start to check app manager database info ...')
        self.adb.executeShellCommand("mount -o remount,rw /system")
        self.adb.push(local='app_manager_scripts/sqlite3', remote='/system/bin')
        userID = self.uut_owner.get_user_id()
        db = self.adb.executeShellCommand("sqlite3 /data/wd/appmgr/db/index.db .dump | grep {0} | grep '{1}'"
            .format(self.app_id, userID))[0]
        while 'Text file busy' in db:
            db = self.adb.executeShellCommand("sqlite3 /data/wd/appmgr/db/index.db .dump | grep {0} | grep '{1}'"
                .format(self.app_id, userID))[0]
            time.sleep(1)
        if db:
            raise self.err.TestFailure('The userID({0}) with appID({1}) is not in database, test Failed !!!'
                .format(userID, self.app_id))


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Reboot system during uninstallation Test Script ***
        Examples: ./run.sh app_manager_scripts/concur_reboot_uninstall_app.py --uut_ip 10.92.224.68 -appid com.wdc.importapp.ibi\
        """)

    parser.add_argument('-appid', '--app_id', help='App ID to installed')

    test = RebootSystemDuringUninstallApp(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
