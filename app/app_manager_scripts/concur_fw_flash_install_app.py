# -*- coding: utf-8 -*-
""" Test case to test install app while FW flashing progress is ongoing
    https://jira.wdmv.wdc.com/browse/KAM-32652
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import os
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from app_manager_scripts.install_app import InstallApp
from bat_scripts_new.fw_update_utility import FWUpdateUtility
from platform_libraries.test_thread import MultipleThreadExecutor


class InstallAppDuringFWFlash(TestCase):

    TEST_SUITE = 'APP_Manager_Test'
    TEST_NAME = 'KAM-32652 - Install app while FW flashing progress is ongoing'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-32652'
    PRIORITY = 'Critical'
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
        self.fwupdate = FWUpdateUtility(env_dict)

    def before_test(self):
        self.fw_flash_prepare()   

    def test(self):
        self.concurrent_fwupdate_install_app()
        self.install_app.timeout = 10
        self.install_app.check_app_status()
        self.log.info('Wait 2 mins to let app update check finished')
        time.sleep(60*2)
        self.install_app.get_pm_list_and_app_logcat_logs()
        if 'Deleted app with port 0' in self.install_app.logcat_check:
            self.log.warning('Deleted app with port 0 found! The app has been deleted because app '
                'installation has been interrupted during reboot.')
            self.log.warning('Start to install_app again ...')
            self.install_app.install_app()
            self.install_app.timeout = 60*15
            self.install_app.check_app_status()
            self.install_app.get_pm_list_and_app_logcat_logs()
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

    def concurrent_fwupdate_install_app(self):
        mte = MultipleThreadExecutor(logging=self.log.info)
        mte.append_thread_by_func(target=self.install_app_only)
        mte.append_thread_by_func(target=self.fw_flashing_and_wait_boot_completed)
        mte.run_threads()

    def after_test(self):
        self.install_app.after_test()

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Install app while FW flashing progress is ongoing Test Script ***
        Examples: ./run.sh app_manager_scripts/concur_fw_flash_install_app.py --uut_ip 10.92.224.68 -appid com.wdc.importapp.ibi -chkapp\
        """)

    parser.add_argument('-appid', '--app_id', help='App ID to installed')
    parser.add_argument('-chkapp', '--check_app_install', help='Remove app before start install app test', action='store_true')
    parser.add_argument('-uninstall_app', '--uninstall_app', help='Uninstall installed app after test', action='store_true')

    test = InstallAppDuringFWFlash(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
