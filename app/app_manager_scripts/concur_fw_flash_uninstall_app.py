# -*- coding: utf-8 -*-
""" Test case to test uninstall app while FW download progress is ongoing
    https://jira.wdmv.wdc.com/browse/KAM-32653
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import os
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from bat_scripts_new.fw_update_utility import FWUpdateUtility
from platform_libraries.test_thread import MultipleThreadExecutor


class UninstallAppDuringFWFlash(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32653 - Un-install app while FW download progress is ongoing'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32653'
    PRIORITY = 'Critical'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.app_id = None
        self.check_pm_list = False

    def init(self):
        env_dict = self.env.dump_to_dict()
        self.fwupdate = FWUpdateUtility(env_dict)

    def before_test(self):
        pm_list_check = self.adb.executeShellCommand('pm list package | grep {}'.format(self.app_id))
        if not pm_list_check[0]:
            raise self.err.TestSkipped('There are no App({0}) installed ! Skipped the Uninstall App test !'.format(self.app_id))
        self.fw_flash_prepare()

    def test(self):
        self.concurrent_fwupdate_uninstall_app()
        # Check logs and pm list
        if self.check_pm_list:
            pm_list_check = self.adb.executeShellCommand('pm list package | grep {}'.format(self.app_id))
            if pm_list_check[0]:
                raise self.err.TestFailure('{} App still in the pm list ! Test Failed !!!'.format(self.app_id))
        self.check_appmgr_db_uninstall()
        self.log.info('App({}) has been uninstalled. Test PASSED !!!'.format(self.app_id))

    def uninstall_app_only(self):
        self.uut_owner.uninstall_app(self.app_id)

    def concurrent_fwupdate_uninstall_app(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        mte.append_thread_by_func(target=self.uninstall_app_only)
        mte.append_thread_by_func(target=self.fw_flashing_and_wait_boot_completed)
        mte.run_threads()

    def fw_flash_prepare(self):
        self.fwupdate.local_image = True
        self.fwupdate.noserial = False
        self.fwupdate.init()
        self.fwupdate.before_test()

        self.log.info('Creating OTA dir {}'.format(self.fwupdate.ota_folder))
        self.adb.executeShellCommand(cmd='mkdir -p {}'.format(self.fwupdate.ota_folder))
        # Remove any image files if already existing
        self.log.info('Removing any files if they exist')
        self.adb.executeShellCommand(cmd='rm -rf {}*'.format(self.fwupdate.ota_folder))
        # Push image file
        self.local_image = os.path.join(self.fwupdate.build_name, self.fwupdate.image)
        self.log.info('Pushing img file to device, this may take a while..')
        dl_md5sum = self.adb.executeCommand('cat {}.md5'.format(self.local_image), consoleOutput=False)[0].split()[0]
        local_md5sum = self.adb.executeCommand('md5sum {}'.format(self.local_image),
                                               consoleOutput=False)[0].strip().split()[0]
        self.adb.push(local=self.local_image, remote=self.fwupdate.ota_folder, timeout=self.fwupdate.run_cmd_timeout)
        push_md5sum = self.adb.executeShellCommand(cmd='busybox md5sum {0}/{1}'.format(self.fwupdate.ota_folder, self.fwupdate.image),
                                                    timeout=120, consoleOutput=False)[0].strip().split()[0]
        self.log.info('Compare checksum..')
        self.log.info('dl_md5sum = {0}, local_md5sum = {1}, push_md5sum = {2}'.format(dl_md5sum, local_md5sum, push_md5sum))
        if dl_md5sum == local_md5sum == push_md5sum:
            self.log.info('FW install.img md5sum are all the same, can be start to execute fw flash ...')
            self.adb.start_otaclient()
        else:
            raise self.err.TestSkipped('Firmware image md5sum are not the same, skip the test !')

    def fw_flashing_and_wait_boot_completed(self):
        self.adb.executeShellCommand(cmd='busybox nohup fw_update {0}{1} -v {2}'
                                     .format(self.fwupdate.ota_folder, self.fwupdate.image, self.fwupdate.version),
                                     timeout=self.fwupdate.run_cmd_timeout)
        self.log.info('Expect device do rebooting ...')
        timeout = 60*10
        if not self.adb.wait_for_device_to_shutdown(timeout=timeout):
            raise self.err.TestFailure('Reboot device: FAILED. Device not shutdown.')
        self.log.info('Wait for device boot completed...')
        time.sleep(20)
        if not self.adb.wait_for_device_boot_completed(timeout=timeout):
            raise self.err.TestFailure('Timeout({}secs) to wait device boot completed..'.format(timeout))
        fw_updated_ver = self.adb.getFirmwareVersion()
        if fw_updated_ver == self.fwupdate.version:
            self.log.info('FW update successfully! FW version: {}'.format(fw_updated_ver))
        else:
            self.log.warning('Notice !!! FW is not match after firmare flash and reboot !!!')
        self.fwupdate.check_restsdk_service()

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
        *** Un-install app while FW flashing progress is ongoing Test Script ***
        Examples: ./run.sh app_manager_scripts/concur_fw_flash_uninstall_app.py --uut_ip 10.92.224.68 -appid com.wdc.importapp.ibi\
        """)

    parser.add_argument('-appid', '--app_id', help='App ID to uninstalled')
    parser.add_argument('-chkpl', '--check_pm_list', help='Check pm list of app package', action='store_true')

    test = UninstallAppDuringFWFlash(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
