# -*- coding: utf-8 -*-
""" Test cases to update Firmware image by using fwupdate command.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import os
import shutil
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase, Settings


class fwUpdateUtility(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Firmware Update Utility Test'

    SETTINGS = Settings(**{
        'disable_firmware_consistency': True,
        'uut_owner': False
    })

    def init(self):
        self.run_cmd_timeout = 60*50
        self.outputpath = '/root/app/output'
        self.ota_folder = '/data/wd/diskVolume0/ota/'
        self.download_path = 'http://10.248.38.53/content/repositories/projects/MyCloudOS'
        self.environment = self.uut.get('environment')
        if self.env.cloud_env != self.environment:
            self.log.warning('Current device env is {0}, is not match with given env {1}, use {2} env to update'
                             .format(self.environment, self.env.cloud_env, self.environment))
            self.env.cloud_env = self.environment
        if self.env.cloud_env == 'qa1':
            self.build_name = 'MCAndroid-QA'
        elif self.env.cloud_env == 'prod':
            self.build_name = 'MCAndroid-prod'
        elif self.env.cloud_env == 'dev1':
            self.build_name = 'MCAndroid'
        elif self.env.cloud_env =='integration':
            self.build_name = 'MCAndroid-integration'
        if self.env.cloud_variant == 'engr':
            self.tag = '-engr'
        elif self.env.cloud_variant == 'user':
            self.tag = '-user'
        else:
            self.tag = ''
        self.image = 'install.img'
        self.model = self.uut.get('model')
        if not self.env.firmware_version:
            self.version = self.uut.get('firmware')
        else:
            self.version = self.env.firmware_version

    def before_test(self):
        self.log.info('***** Start to download firmware image *****')
        tries = 3
        for i in range(tries):
            try:
                # Create ota dir
                self.log.info('Creating OTA dir {}'.format(self.ota_folder))
                self.adb.executeShellCommand(cmd='mkdir -p {}'.format(self.ota_folder))
                # Remove any image files if already existing
                self.log.info('Removing any files if they exist')
                self.adb.executeShellCommand(cmd='rm -rf {}*'.format(self.ota_folder))
                fw_name = '{0}-{1}-ota-installer-{2}{3}.zip'.format(self.build_name, self.version, self.model, self.tag)
                download_url = '{0}/{1}/{2}/{3}'.format(self.download_path, self.build_name, self.version, fw_name)
                check_download_url = self.adb.executeShellCommand('busybox wget --spider {0}'
                                                                  .format(download_url), consoleOutput=False, timeout=10)[0]
                self.log.debug('Check download_url: {}'.format(check_download_url))
                if 'Connection timed out' in check_download_url or '404 Not Found' in check_download_url:
                    raise self.err.StopTest('Cannot access the download path!! Stop Firmware update script!')
                self.adb.executeShellCommand('busybox wget {0} -P {1}'
                                             .format(download_url, self.ota_folder), timeout=self.run_cmd_timeout)
                # Unzip firmware zip file
                self.adb.executeShellCommand('busybox unzip {0}{1} -d {2}'
                                             .format(self.ota_folder, fw_name, self.ota_folder, timeout=self.run_cmd_timeout))
            except Exception as ex:
                if i < tries - 1:
                    self.log.warning('Exception happened on download firmware part, try again..iter: {0}, Err: {1}'
                                     .format(i+1, ex))
                    continue
                else:
                    raise self.err.StopTest('Download fimware failed after retry {0} times. Err: {1}'.format(tries, ex))
            break

    def test(self):
        self.log.info('***** Start to flash firmware image: {} *****'.format(self.version))
        cbr = self.adb.executeShellCommand('cat /proc/device-tree/factory/cbr', consoleOutput=False)[0]
        nbr = self.adb.executeShellCommand('cat /proc/device-tree/factory/nbr', consoleOutput=False)[0]
        bna = self.adb.executeShellCommand('cat /proc/device-tree/factory/bna', consoleOutput=False)[0]
        bootstate = self.adb.executeShellCommand('cat /proc/device-tree/factory/bootstate', consoleOutput=False)[0]
        prop_bootstate = self.adb.executeShellCommand('getprop wd.ota.boot.state', consoleOutput=False)[0]
        self.log.info('cbr = {}'.format(cbr))
        self.log.info('nbr = {}'.format(nbr))
        self.log.info('bna = {}'.format(bna))
        self.log.info('bootstate = {}'.format(bootstate))
        self.log.info('prop_bootstate = {}'.format(prop_bootstate))

        try:
            self.log.info('Executing fw_update binary on device (will timeout and device reboots)')
            self.adb.executeShellCommand(cmd='busybox nohup fw_update {0}{1} -v {2}'
                                         .format(self.ota_folder, self.image, self.version),
                                         timeout=self.run_cmd_timeout-300)
            self.log.info('Expect device do rebooting..')
            if not self.adb.wait_for_device_to_shutdown():
                self.log.error('Reboot device: FAILED. Device not shutdown.')
                raise self.err.TestFailure('Reboot device failed. Device not shutdown.')
            self.log.info('Wait for device boot completed...')
            if not self.adb.wait_for_device_boot_completed():
                self.log.error('Device seems down.')
                raise self.err.TestFailure('Device seems down, device boot not completed')

            # Reset restsdk database
            if self.clean_restsdk_db:
                self.adb.executeShellCommand('stop restsdk-server')
                self.adb.executeShellCommand('umount /data/wd/diskVolume0/restsdk/userRoots')
                self.adb.executeShellCommand('rm -rf /data/wd/diskVolume0/restsdk')
                self.adb.executeShellCommand('start restsdk-server')
                # Check bootable is 0
                if not self.adb.wait_for_device_boot_completed():
                    self.log.error('Bootable is not 0.')
                    raise self.err.TestFailure('Device boot not completed after reset restsdk database')
                starttime = time.time()
                while not (time.time() - starttime) >= 60:
                    curl_localHost = self.adb.executeShellCommand('curl localhost/sdk/v1/device', timeout=10)[0]
                    time.sleep(1)
                    if 'Connection refused' not in curl_localHost:
                        self.log.info("Successfully connected to localhost")
                        break
            time.sleep(30)
        except Exception as ex:
            self.log.exception('Exception during Update test..')
            if os.path.exists(self.outputpath):
                self.log.error('Update Firmware Failed!!!')
                with open("UpdateFailed.txt", "w") as f:
                    f.write('Update Firmware Failed\n')
                shutil.copy('UpdateFailed.txt', '{}/UpdateFailed.txt'.format(self.outputpath))
                self.adb.pull(remote='/cache/ota_install.log', local='{}/ota_install.log'.format(self.outputpath),
                              timeout=self.run_cmd_timeout)
                self.adb.pull(remote='/data/wd/diskVolume0/logs/upload/ota_install.log',
                              local='{}/ota_install.log'.format(self.outputpath), timeout=self.run_cmd_timeout)
                self.adb.pull(remote='/data/wd/diskVolume0/uploadedLogs',
                              local='{}/uploadedLogs'.format(self.outputpath), timeout=self.run_cmd_timeout)
            raise self.err.TestFailure('Test Failed. Err: {}'.format(ex))

        fw_updated_ver = self.adb.getFirmwareVersion()
        if fw_updated_ver == self.version:
            self.log.info('Firmware Update Utility Test PASSED!!')
            if os.path.exists(self.outputpath):
                self.log.info('Update Firmware Success!!!')
                with open("UpdateSuccess.txt", "w") as f:
                    f.write('Update Firmware Success\n')
                shutil.copy('UpdateSuccess.txt', '{}/UpdateSuccess.txt'.format(self.outputpath))
        else:
            raise self.err.TestFailure('Current firmware({}) is not match with update firmware({}), Test Failed!!'
                                       .format(fw_updated_ver, self.version))

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Firmware Update Utility Script ***
        Examples: ./run.sh bat_scripts_new/fwUpdateUtility_directly.py --uut_ip 10.92.224.11 --firmware_version 4.1.0-725 --dry_run\
        """)

    # Test Arguments
    parser.add_argument('--clean_restsdk_db', help='Clear restsdk database', action='store_true', default=False)
    args = parser.parse_args()

    clean_restsdk_db = args.clean_restsdk_db
    test = fwUpdateUtility(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
