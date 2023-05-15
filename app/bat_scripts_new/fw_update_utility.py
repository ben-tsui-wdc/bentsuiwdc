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
from middleware.test_case import TestCase


class FWUpdateUtility(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Firmware Update Utility Test'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-13986,KAM-8766'
    COMPONENT = 'PLATFORM'
    REPORT_NAME = 'Single_run'

    SETTINGS = {
        'disable_firmware_consistency': True,
        'uut_owner': False
    }

    def declare(self):
        self.clean_restsdk_db = False
        self.local_image = False
        self.keep_fw_img = False
        self.disable_ota = False
        self.noserial = False
        self.file_server_ip = 'fileserver.hgst.com'
        self.rename_name = 'fw_update.mv'
        self.rename_fwupdate = False
        self.led_state = ''

    def init(self):
        self.run_cmd_timeout = 60*45
        self.outputpath = '/root/app/output'
        self.ota_folder = '/data/wd/diskVolume0/ota/'
        self.environment = self.uut.get('environment')
        if self.env.cloud_env != self.environment:
            if self.env.cloud_env == 'dev' and self.environment == 'dev1':
                self.log.warning('Given env is {0}, and current device env is {1}, skip environment check ...'
                                    .format(self.env.cloud_env, self.environment))
            else:
                self.log.warning('Current device env is {0}, is not match with given env {1}, use {2} env to update'
                                    .format(self.environment, self.env.cloud_env, self.environment))
                self.env.cloud_env = self.environment
        if self.local_image:
            self.download_path = 'ftp://ftp:ftppw@{}/firmware'.format(self.file_server_ip)
        else:
            if self.env.cloud_env == 'dev':
                self.download_path = 'http://repo.wdc.com/content/repositories/projects/MyCloudOS-Dev'
            else:
                self.download_path = 'http://repo.wdc.com/content/repositories/projects/MyCloudOS'
        self.image = 'install.img'
        self.model = self.uut.get('model')
        self.s_build_name = 'MCAndroid'
        if self.env.cloud_env == 'qa1':
            self.build_name = '{}-QA'.format(self.s_build_name)
        elif self.env.cloud_env == 'prod':
            self.build_name = '{}-prod'.format(self.s_build_name)
        elif self.env.cloud_env == 'dev1' or self.env.cloud_env == 'dev':
            self.build_name = self.s_build_name
        elif self.env.cloud_env =='integration':
            self.build_name = '{}-integration'.format(self.s_build_name)
        if self.env.cloud_variant == 'engr':
            self.tag = '-engr'
        elif self.env.cloud_variant == 'user':
            self.tag = '-user'
        else:
            self.tag = ''
        if not self.env.firmware_version:
            self.version = self.uut.get('firmware')
        else:
            self.version = self.env.firmware_version

    def before_test(self):
        self.log.info('***** Start to download firmware image *****')
        tries = 3
        for i in range(tries):
            try:
                if self.model == 'yoda':
                    fw_name = '{0}-{1}-ota-installer-yodaplus{2}.zip'.format(self.build_name, self.version, self.tag)
                else:
                    fw_name = '{0}-{1}-ota-installer-{2}{3}.zip'.format(self.build_name, self.version, self.model, self.tag)
                if self.build_name in os.listdir('.') and self.keep_fw_img and i == 0:
                    # Only keep firmware image at first-time check,
                    # if i > 0 means download image failed and need to clean the firmware image before next download start
                    if fw_name in os.listdir(self.build_name):
                        self.log.info('Firmware image "{0}" and folder "{1}" exist, keep it'.format(fw_name, self.build_name))
                    else:
                        os.remove(self.build_name)
                else:
                    for dir in os.listdir('.'):
                        if dir.startswith(self.build_name) and '.zip' in dir:
                            self.log.info('Remove unnecessary "{}" files'.format(dir))
                            os.remove(dir)
                        elif self.build_name in dir:
                            self.log.info('Remove unnecessary "{}" folder'.format(dir))
                            shutil.rmtree(dir)
                if not self.keep_fw_img or self.build_name not in os.listdir('.'):
                    os.mkdir(self.build_name)
                    if self.local_image:
                        download_url = '{0}/{1}'.format(self.download_path, fw_name)
                    else:
                        download_url = '{0}/{1}/{2}/{3}'.format(self.download_path, self.build_name, self.version, fw_name)
                    self.adb.executeCommand('wget -nv -t 10 {}'.format(download_url), timeout=self.run_cmd_timeout)
                    shutil.move(fw_name, os.path.join(self.build_name, fw_name))
                    self.safe_unzip(zip_file=os.path.join(self.build_name, fw_name), extractpath=self.build_name)
                self.log.info(os.listdir(self.build_name))
            except Exception as ex:
                if i < tries - 1:
                    self.log.warning('Exception happened on download firmware part, try again..iter: {0}, Err: {1}'
                                     .format(i+1, ex))
                    continue
                else:
                    if os.path.exists(self.outputpath):
                        self.log.warning('Download Firmware Failed!!!')
                        with open("DownloadFailed.txt", "w") as f:
                            f.write('Download Firmware Failed\n')
                        shutil.copy('DownloadFailed.txt', '{}/DownloadFailed.txt'.format(self.outputpath))
                    raise self.err.StopTest('Download fimware failed after retry {0} times. Err: {1}'.format(tries, ex))
            break

        self.log.info('***** Rename back fw_update binary *****')
        self.adb.executeShellCommand('test -e /system/bin/{0} && mount -o remount,rw /system && mv /system/bin/{0} /system/bin/fw_update'.format(self.rename_name))


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
            # Create ota dir
            self.log.info('Creating OTA dir {}'.format(self.ota_folder))
            self.adb.executeShellCommand(cmd='mkdir -p {}'.format(self.ota_folder))
            # Remove any image files if already existing
            self.log.info('Removing any files if they exist')
            self.adb.executeShellCommand(cmd='rm -rf {}*'.format(self.ota_folder))
            # Push image file
            self.local_image = os.path.join(self.build_name, self.image)
            self.log.info('Pushing img file to device, this may take a while..')
            dl_md5sum = self.adb.executeCommand('cat {}.md5'.format(self.local_image), consoleOutput=False)[0].split()[0]
            local_md5sum = self.adb.executeCommand('md5sum {}'.format(self.local_image),
                                                   consoleOutput=False)[0].strip().split()[0]
            self.adb.push(local=self.local_image, remote=self.ota_folder, timeout=self.run_cmd_timeout)
            push_md5sum = self.adb.executeShellCommand(cmd='busybox md5sum {0}/{1}'.format(self.ota_folder, self.image), timeout=120,
                                                       consoleOutput=False)[0].strip().split()[0]
            self.log.info('Compare checksum..')
            self.log.info('dl_md5sum = {0}, local_md5sum = {1}, push_md5sum = {2}'.format(dl_md5sum, local_md5sum, push_md5sum))
            if dl_md5sum == local_md5sum == push_md5sum:
                self.log.info('Executing fw_update binary on device (will timeout and device reboots)')
                self.adb.start_otaclient()
                self.adb.executeShellCommand(cmd='busybox nohup fw_update {0}{1} -v {2}'
                                             .format(self.ota_folder, self.image, self.version),
                                             timeout=self.run_cmd_timeout)
                if (self.model == 'yodaplus' or self.model == 'yoda') and not self.noserial:
                    self.log.info('Check system log: LED is "Full Solid" when system is updating firmware.')
                    self.led_state = self.serial_client.get_led_state()
                    self.log.info('Led State: {}'.format(self.led_state))
                self.log.info('Expect device do rebooting..')
                if not self.adb.wait_for_device_to_shutdown():
                    self.log.error('Reboot device: FAILED. Device not shutdown.')
                    raise self.err.TestFailure('Reboot device failed. Device not shutdown.')
                time.sleep(20)
                try:
                    if (self.model == 'yodaplus' or self.model == 'yoda') and not self.noserial:
                        self.serial_client.wait_for_boot_complete()
                    self.log.info('Wait for device boot completed...')
                    if not self.adb.wait_for_device_boot_completed(disable_ota=self.disable_ota):
                        self.log.error('Device seems down.')
                        raise
                except Exception as ex:
                    self.log.warning('Exception Message: {}'.format(ex))
                    raise self.err.TestFailure('Device seems down, device boot not completed')
                # For downgrade restsdk database situation
                self.log.info("Check 'wrong version' log exist or not to handle downgrade case ...")
                logcat_wrong_version = self.adb.executeShellCommand("logcat -d | grep 'wrong version'")[0]
                if logcat_wrong_version or self.version.startswith('4.4.1') or self.version.startswith('4.0.1'):
                    self.clean_restsdk_db = True
                # Reset restsdk database
                if self.clean_restsdk_db:
                    self.adb.executeShellCommand('stop restsdk-server')
                    self.adb.executeShellCommand('umount /data/wd/diskVolume0/restsdk/userRoots')
                    self.adb.executeShellCommand('rm -rf /data/wd/diskVolume0/restsdk', timeout=60*5)
                    self.adb.executeShellCommand('start restsdk-server')
                    self.adb.stop_otaclient()
                    if not self.adb.wait_for_device_boot_completed(disable_ota=self.disable_ota):
                        raise self.err.TestFailure('Device boot not completed after reset restsdk database')
                    starttime = time.time()
                    while not (time.time() - starttime) >= 60:
                        curl_localHost = self.adb.executeShellCommand('curl localhost/sdk/v1/device', timeout=10)[0]
                        time.sleep(1)
                        check_list = ['id', 'securityCode', 'localCode', 'active']
                        if 'Connection refused' not in curl_localHost and all(word in curl_localHost for word in check_list):
                            self.log.info("Successfully connected to localhost")
                            break
            else:
                raise self.err.TestFailure('md5sum is not match, stop update firmware image')

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
            self.check_restsdk_service()
            self.log.info('Firmware Update Utility Test PASSED!!')
            if os.path.exists(self.outputpath):
                self.log.info('Update Firmware Success!!!')
                with open("UpdateSuccess.txt", "w") as f:
                    f.write('Update Firmware Success\n')
                shutil.copy('UpdateSuccess.txt', '{}/UpdateSuccess.txt'.format(self.outputpath))
        else:
            if os.path.exists(self.outputpath):
                self.log.error('Update Firmware Failed!!!')
                with open("UpdateFailed.txt", "w") as f:
                    f.write('Update Firmware Failed\n')
                shutil.copy('UpdateFailed.txt', '{}/UpdateFailed.txt'.format(self.outputpath))
            raise self.err.TestFailure('Current firmware({}) is not match with update firmware({}), Test Failed!!'
                                       .format(fw_updated_ver, self.version))

    def check_restsdk_service(self):
        self.start = time.time()
        while not self.is_timeout(60*3):
            # Execute command to check restsdk is running
            grepRest = self.adb.executeShellCommand('ps | grep restsdk')[0]
            if 'restsdk-server' in grepRest:
                self.log.info('Restsdk-server is running\n')
                break
            time.sleep(3)
        else:
            raise self.err.TestFailure("Restsdk-server is not running after wait for 3 mins")

        # Sometimes following error occurred if making REST call immediately after restsdk is running.
        # ("stdout: curl: (7) Failed to connect to localhost port 80: Connection refused)
        # Add retry mechanism for get device info check
        self.start = time.time()
        while not self.is_timeout(60*2):
            # Execute sdk/v1/device command to check device info to confirm restsdk service running properly
            curl_localHost = self.adb.executeShellCommand('curl localhost/sdk/v1/device?pretty=true')[0]
            if 'Connection refused' in curl_localHost:
                self.log.warning('Connection refused happened, wait for 5 secs and try again...')
                time.sleep(5)
            else:
                break
        else:
            raise self.err.TestFailure("Connected to localhost failed after retry for 2 mins ...")

    def is_timeout(self, timeout):
        return time.time() - self.start >= timeout

    def after_test(self):
        if not self.keep_fw_img:
            for item in os.listdir('.'):
                if self.build_name in item:
                    shutil.rmtree(item)
        time.sleep(5)

        if self.rename_fwupdate:
            self.log.info('***** Rename fw_update binary *****')
            self.adb.executeShellCommand('test -e /system/bin/fw_update && mount -o remount,rw /system && mv /system/bin/fw_update /system/bin/{}'.format(self.rename_name))

    def get_serial_led(self):
        return self.led_state

    def safe_unzip(self, zip_file, extractpath='.'):
        import zipfile
        self.log.info('Start unzip file')
        with zipfile.ZipFile(zip_file, 'r') as zf:
            for member in zf.infolist():
                abspath = os.path.abspath(os.path.join(extractpath, member.filename))
                if abspath.startswith(os.path.abspath(extractpath)):
                    zf.extract(member, extractpath)


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Firmware Update Utility Script ***
        Examples: ./run.sh bat_scripts/fw_update_utility.py --uut_ip 10.92.224.68 --firmware_version 4.1.0-725 --cloud_env dev1\
        """)

    # Test Arguments
    parser.add_argument('--clean_restsdk_db', help='Clear restsdk database', action='store_true', default=False)
    parser.add_argument('--local_image', action='store_true', default=False,
                        help='Download ota firmware image from local file server')
    parser.add_argument('--keep_fw_img', action='store_true', default=False, help='Keep downloaded firmware')
    parser.add_argument('--file_server_ip', default='fileserver.hgst.com', help='File server IP address')
    parser.add_argument('--disable_ota', help='Disabled OTA client after test', action='store_true')
    parser.add_argument('--noserial', help='Disabled serial console check point', action='store_true')
    parser.add_argument('--rename_name', default='fw_update.mv', help='Rename name of fw_update binary')
    parser.add_argument('--rename_fwupdate', action='store_true', default=False, help='Rename fw_update binary after updated')
    args = parser.parse_args()

    test = FWUpdateUtility(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
