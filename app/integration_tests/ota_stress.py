# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import time
import re
import os
import shutil
import json
import string
import numpy as np


# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase, Settings
from platform_libraries.cloud_api import CloudAPI
from bat_scripts_new.fw_update_utility import FWUpdateUtility
from bat_scripts_new.factory_reset import FactoryReset
from jenkins_scripts.update_bucket import OTABucket
from platform_libraries.pyutils import retry

class OTAStress(FWUpdateUtility):

    TEST_SUITE = 'OTA_Stress_Test'
    TEST_NAME = 'OTA_Stress_Test'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-35796,KAM-22360, KAM-22486'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None
    REPORT_NAME = 'OTA'

    # Do not attach owner when the test starts
    SETTINGS = Settings(**{
        'uut_owner': True,
        'disable_firmware_consistency': True
    })

    # Max retries when ota is failed
    MAX_RETRIES = 10

    # OTA update status lists
    OTA_INPROGRESS = ['downloading', 'downloaded', 'unzipping', 'unzipped',
                      'updating', 'updated', 'rebootPending', 'updateReboot',
                      'init', 'bootloaderUpdating', 'bootloaderUpdated' ]
    OTA_FAILED = ['downloadFail', 'unzipFail', 'updateFail', 'bootloaderUpdateFail', 'updateFailAfterReboot']
    OTA_COMPLETE = 'updateOk'

    # Data info for checking integrity
    LOCAL_UPLOAD_FOLDER = os.path.join(os.getcwd(), 'upload_data_before_ota')
    LOCAL_FILE_MD5_DICT = dict()
    NAS_FILE_MD5_DICT = dict()
    # Dummyfile used for upload/download file after each iteration
    LOCAL_DUMMY_MD5 = ""
    TEST_FILE = 'dummyfile'

    def init(self):
        self.failed_count = 0
        self.skipped_count = 0
        self.platform = self.adb.getModel()
        self.cloud_obj = CloudAPI(env=self.env.cloud_env)
        self.file_list = []
        self.migrate_time_list = []
        self.migrate_from_version = None
        self.migrate_to_version = None
        self.migrated = None
        self.outputpath = '/root/app/output'

    def before_loop(self):

        def _local_md5_checksum(path):
            # Only use when the data set is downloaded from file server
            response = os.popen('md5sum {}'.format(path))
            if response:
                result = response.read().strip().split()[0]
                return result
            else:
                self.log.error("There's no response from md5 checksum")
                return None

        def _create_random_file(file_name, local_path='', file_size='1048576'):
            # Default 1MB dummy file
            self.log.info('Creating file: {}'.format(file_name))
            try:
                with open(os.path.join(local_path, file_name), 'wb') as f:
                    f.write(os.urandom(int(file_size)))
            except Exception as e:
                self.log.error('Failed to create file: {0}, error message: {1}'.format(local_path, repr(e)))
                raise

        self.log.info("[Before Loop]")

        self.log.warning("Check if test_fw version matches the bucket to_version")
        self.log.debug('Test environment: {}'.format(self.env.cloud_env))
        self.log.debug('OTA_bucket_id: {}'.format(self.ota_bucket_id))
        self.log.debug('Platform model: {}'.format(self.platform))
        OTA_BUCKET = OTABucket(env=self.env.cloud_env, ver=None, bid=self.ota_bucket_id, model=self.platform)
        bucket_info = OTA_BUCKET.get_ota_specific_buckets_info()
        self.log.warning('bucket_id: {}'.format(bucket_info.get('bucket_id')))
        self.log.warning('bucket_name: {}'.format(bucket_info.get('bucket_name')))
        self.log.warning('device_type: {}'.format(bucket_info.get('device_type')))
        self.log.warning('url: {}'.format(bucket_info.get('url')))
        self.log.warning('md5sum: {}'.format(bucket_info.get('md5sum')))
        self.log.warning('sha256sum: {}'.format(bucket_info.get('sha256sum')))
        self.log.warning('start_version: {}'.format(bucket_info.get('start_version')))
        self.log.warning('timestamp: {}'.format(bucket_info.get('timestamp')))
        self.log.warning('is_default: {}'.format(bucket_info.get('is_default')))
        self.log.warning('is_immediate: {}'.format(bucket_info.get('is_immediate')))
        self.log.warning('update_uboot: {}'.format(bucket_info.get('update_uboot')))
        bucket_to_version = bucket_info.get('to_version')
        self.log.warning("Bucket to_version: {}".format(bucket_to_version))

        if self.test_fw == "Auto" or self.test_fw == "auto" or self.test_fw == "None" or not self.test_fw:
            self.log.warning("Test version is not specified, will use {} to test".format(bucket_to_version))
            self.test_fw = bucket_to_version
        else:
            if self.test_fw != bucket_to_version:
                self.log.warning("Test version is not match the to_verion in bucket, will update the bucket")
                OTA_BUCKET.ver = self.test_fw
                OTA_BUCKET.update_bucket(update_bucket_name=None, update_start_version=None)
                bucket_to_version = OTA_BUCKET.get_ota_specific_buckets_info()['to_version']
                self.log.warning("Double check bucket new to_version is: {}".format(bucket_to_version))
                if self.test_fw != bucket_to_version:
                    self.failed_count += 1
                    raise self.err.TestFailure("Failed to update bucket to specified version! Stop the test!")
            else:
                self.log.info("Test version matches the to_version in bucket, keep testing")

        if self.usb_folder:
            self.log.info("The data set for I/O test will be from USB: {}".format(self.usb_folder))
            usb_mount_path = '/mnt/media_rw'
            usb_dir = self.adb.executeShellCommand('ls {}'.format(usb_mount_path))[0].strip()
            if not usb_dir:
                self.log.error("USB is not mounted!!!".format(file))

            self.log.info("Checking the file list in USB and calculating the MD5 checksum, this step may take some time...")
            usb_files = self.adb.executeShellCommand('ls {0}/{1}/{2}'.format(usb_mount_path, usb_dir, self.usb_folder),
                                                     consoleOutput=False, timeout=3600)[0]
            lists = usb_files.split()
            self.log.warning("File numbers: {}".format(len(lists)))
            for file_name in lists:
                if any(char.isdigit() for char in file_name):
                    md5sum = self.adb.executeShellCommand('busybox md5sum {0}{1}/{2}'
                                                          .format(usb_mount_path, usb_dir, file_name),
                                                          consoleOutput=False, timeout=300)[0].split()[0]
                    self.LOCAL_FILE_MD5_DICT.update({file_name: md5sum})
        else:
            self.log.info("Prepare local test folder")
            if os.path.exists(self.LOCAL_UPLOAD_FOLDER):
                shutil.rmtree(self.LOCAL_UPLOAD_FOLDER)
            os.mkdir(self.LOCAL_UPLOAD_FOLDER)

            self.log.info("Download test files from file server to upload folder")
            download_path = '{0}{1}'.format('ftp://ftp:ftppw@{}'.format(self.file_server_ip), self.dir_in_file_server)
            cur_dir = self.dir_in_file_server.count('/')
            cmd = 'wget --no-host-directories --cut-dirs={0} -r {1} -P {2}'.format(cur_dir, download_path,
                                                                                   self.LOCAL_UPLOAD_FOLDER)
            if self.private_network:
                cmd += ' --no-passive'
            os.popen(cmd)

            for (dirpath, dirnames, filenames) in os.walk(self.LOCAL_UPLOAD_FOLDER):
                self.file_list.extend(filenames)
                break

            self.log.info("Calculating the MD5 checksum, this step may take some time...")
            # Get the md5 checksum list for comparison standard
            for file in self.file_list:
                md5 = _local_md5_checksum(os.path.join(self.LOCAL_UPLOAD_FOLDER, file))
                if md5:
                    self.LOCAL_FILE_MD5_DICT[file] = md5
                else:
                    self.log.error("Failed to get MD5 checksum of file: {}".format(file))

        # Dummyfile used for upload/download file after each iteration
        _create_random_file(self.TEST_FILE)
        self.LOCAL_DUMMY_MD5 = _local_md5_checksum(self.TEST_FILE)
        if not self.LOCAL_DUMMY_MD5:
            self.failed_count += 1
            raise self.err.TestFailure('Failed to get the local dummy md5 checksum!')
        self.log.warning("Local dummyfile MD5 Checksum: {}".format(self.LOCAL_DUMMY_MD5))

        # Get device mac address
        self.log.info('Get device mac address ...')
        if self.platform == 'monarch' or self.platform == 'pelican':
            self.mac_address = self.adb.get_mac_address(interface='eth0')
        if self.platform == 'yoda' or self.platform == 'yodaplus':
            self.mac_address = self.adb.get_mac_address(interface='wlan0')

    def before_test(self):
        pass

    def test(self):

        def _compare_filename(file_list_before, file_list_after):
            diff = list(set(file_list_before) ^ set(file_list_after))
            if diff:
                self.log.warning("File names are not match! The different files:{}".format(diff))
                return False
            else:
                self.log.info("File names are match")
                return True

        def _compare_checksum(checksum_dict_before, checksum_dict_after):
            diff = list(file for file in checksum_dict_before.keys() \
                        if checksum_dict_before.get(file) != checksum_dict_after.get(file))
            if diff:
                self.log.warning("MD5 comparison failed! The different files:")
                for file in diff:
                    self.log.warning("{}: md5 before [{}], md5 after [{}]".
                                     format(file, checksum_dict_before.get(file), checksum_dict_after.get(file)))
                return False
            else:
                return True

        def _ota_status():
            ota_info = self.adb.executeShellCommand('logcat -d | grep "ota_update_status" | grep "{}"'.
                                                    format(self.test_fw), consoleOutput=False)[0]
            self.log.debug("OTA info: {}".format(ota_info))
            latest_ota_info = ota_info.strip().split('\r\n')[-1]
            ota_update_status = re.match(r'.+\"status\":\"(.+)\","time".+', latest_ota_info)
            if ota_update_status:
                return ota_update_status.group(1)
            else:
                return None

        def _migrate_status():
            # migrate_process = self.adb.executeShellCommand('logcat -d | grep "migrateStepEnd"', consoleOutput=False)[0].strip()
            migrate_info = self.adb.executeShellCommand('logcat -d | grep "migrated" | grep "Migrate" | grep -v "MigratedLocal"',
                                                        consoleOutput=False)[0].strip()

            if not migrate_info:
                self.log.error("Cannot find migration information, test failed!")
                return False

            """
            # This step is because some migration process has non-ascii code inside
            printable = set(string.printable)
            migrate_process = filter(lambda x: x in printable, migrate_process)
            self.log.debug("Migrate process: {}".format(migrate_process))

            # There will be many process results, e.g. db 68->69->70->...->88, we need to parser and calculate the sum
            migrate_time_sum = 0.0
            migrate_process = migrate_process.split()
            step_index = 1
            for each_migrate in migrate_process:
                migrate_time = re.match(r'.+\"elapsedTime\":(.+),"file".+', each_migrate)
                if migrate_time:
                    time_temp = re.sub("[^0-9.]", "", migrate_time.group(1))
                    self.log.info("Step {}: {}ms".format(step_index, time_temp))
                    migrate_time_sum += float(time_temp)
                    step_index += 1
            """
            printable = set(string.printable)
            migrate_info = filter(lambda x: x in printable, migrate_info)
            self.log.debug("Migrate info: {}".format(migrate_info))
            migrate_time = re.match(r'.+\"elapsedTime\":(.+),"file".+', migrate_info)
            if migrate_time:
                time_temp = re.sub("[^0-9.]", "", migrate_time.group(1))
                migrate_time_sum = float(time_temp)
            migrate_info = re.match(r'.+(\{.+\})', migrate_info)
            migrate_info = migrate_info.group(1).replace("'", "\"")
            migrate_info = json.loads(migrate_info)
            migrate_from = migrate_info.get('from')
            migrate_to = migrate_info.get('to')

            self.log.warning("from: {}".format(migrate_from))
            self.log.warning("to: {}".format(migrate_to))
            self.log.warning("Total migrage time: {}".format(int(migrate_time_sum)))

            self.migrate_time_list.append(int(migrate_time_sum))
            # Todo: Get DB version from adb and compare if it's correct
            if not self.migrate_from_version: self.migrate_from_version = migrate_from
            if not self.migrate_to_version: self.migrate_to_version = migrate_to
            return True

        def _check_if_ota_is_running():
            self.log.info("To avoid device ota to default bucket, print the fw update and ota update logs")
            fw_update_status = self.adb.executeShellCommand("ps | grep fw_update")[0]
            self.log.warning("FW update status: {}".format(fw_update_status))
            ota_update_status = self.adb.executeShellCommand("logcat -d | grep ota_update_status")[0]
            self.log.warning("OTA update status: {}".format(ota_update_status))
            lock_file_status = self.adb.executeShellCommand("ls | /tmp/ota_lock")[0]
            self.log.warning("Lock file status: {}".format(lock_file_status))
            self.log.info("Stop otaclient again, just to make sure it's not running")
            self.adb.executeShellCommand("stop otaclient")

        def _fill_up_disk_volume(blocksize=1024*1024, count=105*1024):
            # not completed
            self.log.info('Create dd file to fill up the disk volume ...')
            self.adb.executeShellCommand('dd if=/dev/zero of=big.img bs={} count={}')

        def _recreated_diskVolume0_to_small_size(size=105*1024*1024):
            # not completed
            if self.uut.get('model') == 'monarch':
                self.log.info('Start to re-create diskVolume0 to small size')
                self.adb.executeShellCommand('mount -o remount,rw /system')
                self.adb.executeShellCommand('mv /system/bin/disk_manager_monarch.sh /system/bin/d.sh')
                self.log.info('Do factory reset in _recreated_diskVolume0_to_small_size ...')
                try:
                    _check_if_ota_is_running()
                    env_dict = self.env.dump_to_dict()
                    env_dict['Settings'] = ['uut_owner=False']
                    factory_reset = FactoryReset(env_dict)
                    factory_reset.no_rest_api = True
                    factory_reset.disable_ota = self.disable_ota
                    factory_reset.test()
                    time.sleep(60)
                except Exception as e:
                    self.log.error('Failed to run factory reset in _recreated_diskVolume0_to_small_size! Error message: {}'.format(repr(e)))
                    test_result = 'Failed'
                self.adb.executeShellCommand('mke2fs -t ext4 -m 1 -E lazy_itable_init=0,lazy_journal_init=0 /dev/block/sataa24 {}'.format(size))
                self.adb.executeShellCommand('mount -o remount,rw /system')
                self.adb.executeShellCommand('mv /system/bin/d.sh /system/bin/disk_manager_monarch.sh')
                self.adb.reboot_device_and_wait_boot_up()

        # Setup initial value
        if self.database_migration:
            db_change = True
        else:
            db_change = False

        self.log.warning("db_change: {}".format(db_change))
        # Todo: Get the DB version and check if it will be migrated
        """
        db_change = False
        if self.database_migration:
            db_change = True
        else:
            start_fw_prefix = self.start_fw.split('-')[0]
            test_fw_prefix = self.test_fw.split('-')[0]
            if [(start_fw_prefix in ('4.0.1', '4.1.1', '4.4.1') and test_fw_prefix in ('5.0.0', '5.0.1')) or
                (start_fw_prefix != '5.1.0' and test_fw_prefix == '5.1.0')]:
                db_change = True
            else:
                db_change = False
        """
        test_result = ''
        self.log.info('### Step 1: Downgrade the device to {}'.format(self.start_fw))
        self.env.firmware_version = self.start_fw
        if self.adb.getFirmwareVersion() == self.start_fw:
            self.log.info('Firmware version is already {}, no need to update'.format(self.start_fw))
        else:
            retry = 0
            max_retries = 3
            while True:
                try:
                    self.log.warning('enter fwupdate utility init')
                    super(OTAStress, self).init()
                    self.log.warning('enter fwupdate utility before test')
                    super(OTAStress, self).before_test()
                    self.log.warning('enter fwupdate utility test')
                    super(OTAStress, self).test()
                    self.log.info("Downgrade to {} successfully".format(self.start_fw))
                    break
                except self.err.TestFailure as e:
                    self.log.warning('TestFailure happening: {}'.format(repr(e)))
                except Exception as ex:
                    self.log.warning('Exception happening: {}'.format(repr(ex)))
                self.log.warning('Failed to downgrade the device to {}! {} times retries remaining...'.
                                 format(self.start_fw, (max_retries - retry)))
                retry += 1
                if retry > max_retries:
                    self.log.error('Retried {} times but still failed to downgrade firmware to {}! Skip the test!'.
                                   format(max_retries, self.start_fw))
                    test_result = 'Skipped'
                    break

        if test_result not in ('Failed', 'Skipped'):
            
            self.log.info('### Step 2: Run factory reset to make sure DB is correct')
            '''
            if db_change:
                self.log.warning('Though fw_update_utility already cover this situation, we better run this step again')
                self.adb.executeShellCommand('stop restsdk-server')
                self.adb.executeShellCommand('umount /data/wd/diskVolume0/restsdk/userRoots')
                self.adb.executeShellCommand('rm -rf /data/wd/diskVolume0/restsdk')
                self.adb.executeShellCommand('start restsdk-server')
                self.adb.executeShellCommand('busybox nohup reboot')  # reboot the device or bootable is always 0
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
            '''
            try:
                _check_if_ota_is_running()
                env_dict = self.env.dump_to_dict()
                env_dict['Settings'] = ['uut_owner=False']
                factory_reset = FactoryReset(env_dict)
                factory_reset.no_rest_api = True
                factory_reset.disable_ota = self.disable_ota
                factory_reset.test()
                self.log.warning("Sleep 60 secs after factory reset for old firmware versions")
                time.sleep(60)
            except Exception as e:
                self.log.error('Failed to run factory reset! Error message: {}'.format(repr(e)))
                test_result = 'Failed'

            if self.resumable_test:
                self.log.warning("Modify the download timeout to 30 secs to run resumable test")
                self.adb.executeShellCommand("mount -o remount,rw /system")
                self.adb.executeShellCommand('echo \'downloadTimeout = 30\' >> /system/etc/otaclient.toml')
                result = self.adb.executeShellCommand('cat /system/etc/otaclient.toml')[0]
                self.log.warning(result)

            self.log.info('### Step 3: Record the device ID and upload some data before OTA')
            _check_if_ota_is_running()
            self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']})
            device_id_before = self.uut_owner.get_local_code_and_security_code()[0]
            self.log.warning('Device ID (Before OTA): {}'.format(device_id_before))

            if self.usb_folder:
                self.uut_owner.usb_slurp(folder_name=self.usb_folder)
            else:
                for index, file in enumerate(self.file_list):
                    with open(os.path.join(self.LOCAL_UPLOAD_FOLDER, file), 'rb') as f:
                        self.log.debug("Uploading file: {0} into test device".format(file))
                        if not self.start_fw.startswith('5.0'): # upload files not support on cognito if start firmware < 5.1.0
                            self.uut_owner.chuck_upload_file(file_object=f, file_name=file)
                        else:
                            self.log.warning('Start firmware is old than 5.1.0, skip upload files steps...')

            self.log.info('### Step 4: Wait for OTA and check update status')
            self.log.info('Checking if device id is added in OTA bucket before')
            if self.ota_bucket_id != "":
                self.log.info("Specified ota_bucket_id:{}".format(self.ota_bucket_id))
                bucket_id = self.ota_bucket_id
            else:
                self.log.info("Checking the bucket id from cloud server")
                bucket_id = self.cloud_obj.get_ota_buckets_info(self.test_fw, self.platform)['bucket_id']

            self.log.debug('bucket_id: {}'.format(bucket_id))
            retry_times = 10
            while retry_times > 0:
                device_info = self.adb.executeShellCommand('curl localhost/sdk/v1/device')[0]
                if '"id":' in device_info:
                    device_id = json.loads(device_info)['id']
                    break
                else:
                    self.log.warning(
                        'No device id information, wait 30 secs and retry, {} times remaining..'.format(retry_times))
                    retry_times -= 1
                    if retry_times == 0:
                        self.failed_count += 1
                        raise self.err.TestFailure('Cannot get device id!')
                    time.sleep(30)

            self.cloud_obj.register_device_in_cloud(self.platform, device_id, self.start_fw)
            result = self.cloud_obj.check_device_in_ota_bucket(bucket_id, device_id, self.adb)
            if not result:
                device_id_list = []
                device_id_list.append(device_id)
                self.cloud_obj.add_device_in_ota_bucket(bucket_id, device_id_list)

            lock_file_status = self.adb.executeShellCommand("ls | /tmp/ota_lock")[0]
            self.log.warning("Lock file status: {}".format(lock_file_status))
            if lock_file_status != "":
                self.adb.executeShellCommand("rm /tmp/ota_lock")

            self.adb.start_otaclient()
            self.adb.executeShellCommand("start otaclient")
            self.timing.reset_start_time()
            retry_times = 0
            restart_ota_count = 0
            expect_fw_prefix = self.test_fw.split('-')[0]
            expect_fw_suffix = self.test_fw.split('-')[1]
            while not self.timing.is_timeout(self.ota_timeout):
                try:
                    ota_status = _ota_status()
                    if not ota_status:
                        cbr = self.adb.executeShellCommand('cat /proc/device-tree/factory/cbr', consoleOutput=False)[0]
                        current_fw = self.adb.getFirmwareVersion()
                        full_ota_info = self.adb.executeShellCommand('logcat -d | grep "ota_update_status"', consoleOutput=False)[0]
                        self.log.info('Current CBR: {}'.format(cbr))
                        self.log.info('Current FW: {}'.format(current_fw))
                        self.log.debug('Full OTA info: {}'.format(full_ota_info))

                        if restart_ota_count >= 80:
                            self.log.info('Already retry more than 20 mins, sometimes the "updateOK" will not be in logcat, compare the version directly')
                            if current_fw == self.test_fw:
                                test_result = 'Passed'
                                break
                            else:
                                if current_fw:
                                    current_fw_prefix = current_fw.split('-')[0]
                                    current_fw_suffix = current_fw.split('-')[1]
                                    if current_fw_prefix == expect_fw_prefix and int(current_fw_suffix) > int(expect_fw_suffix):
                                        self.log.warning("Current firmware is newer then expect version,\
                                                          mark the test as Passed but need to check if bucket to_version is changed")
                                        test_result = 'Passed'
                                        break
                            self.log.info("Firmware version not match, keep retrying...")

                        if restart_ota_count % 40 == 0:
                            self.log.warning('Restart otaclient for every 10 mins')
                            self.adb.executeShellCommand("stop otaclient")
                            time.sleep(10)
                            self.adb.executeShellCommand("start otaclient")
                        
                        self.timing.finish()
                        self.log.warning('[{} secs] Cannot find any ota update status info, wait for 15 secs'.
                                         format(round(self.timing.get_elapsed_time(), 1)))
                        restart_ota_count += 1
                        time.sleep(15)
                    else:
                        self.timing.finish()
                        self.log.info("[{0} secs] OTA status: {1}".
                                      format(round(self.timing.get_elapsed_time(), 1), ota_status))
                        if ota_status == self.OTA_COMPLETE:
                            self.log.info('OTA complete! Check if the firmware version is correct')
                            curr_fw = self.adb.getFirmwareVersion()
                            self.log.info('Get wiri version')
                            self.log.info('Wait 10 secs to let cloud database sync wiri version...')
                            time.sleep(10)
                            wiri_fw = self.cloud_obj.get_device_info_with_mac(mac_address=self.mac_address)['firmware']['wiri']
                            self.log.info('Wiri version is: {}'.format(wiri_fw))
                            self.timing.reset_start_time()
                            while not curr_fw == self.test_fw == wiri_fw:
                                self.log.warning('Need more time to let cloud database sync wiri version ... wait 20 secs')
                                time.sleep(20)
                                wiri_fw = self.cloud_obj.get_device_info_with_mac(mac_address=self.mac_address)['firmware']['wiri']
                                self.log.warning('Wiri version is: {}'.format(wiri_fw))
                                if curr_fw == self.test_fw == wiri_fw:
                                    test_result = 'Passed'
                                    break
                                if self.timing.is_timeout(180):
                                    self.log.error("Firmware version not match! Expect: {}, Current: {}, Wiri: {}".format(self.test_fw, curr_fw, wiri_fw))
                                    test_result = 'Failed'
                                    break
                            else:
                                test_result = 'Passed'
                                break
                        elif ota_status in self.OTA_INPROGRESS:
                            if (ota_status == 'updating' or ota_status == 'updateReboot') and db_change:
                                if self.serial_client:
                                    def _check_migrated_and_RTD1295(self):
                                        if self.serial_client.serial_wait_for_filter_string('"msgid":"migrated",|Hardware name: Realtek_RTD1295', 3, False):
                                            self.migrated = True
                                            return True
                                        return False
                                    self.log.info('Clean serial console log read queue...')
                                    self.serial_client.init_read_queue()
                                    if self.serial_client.serial_wait_for_string('init: stopping android....', timeout=60*6, raise_error=False):
                                        self.log.info('Device start to rebooting ...')
                                    if self.serial_client.serial_wait_for_filter_string('"msgid":"migrated",|Hardware name: Realtek_RTD1295|Hardware name: Realtek_RTD1296', 60):
                                        self.log.warning('Twice reboot happening, skip the db migration check ...')
                                        db_change = False
                                        self.log.warning("db_change: {}".format(db_change))
                                else:
                                    self.log.warning('No serial_client, skipped migrated and db migration for twice reboot check')
                                    self.migrated = False
                                    db_change = False
                                '''
                                retry(
                                    func=self.serial_client.get_migrated_info, raise_error=False,
                                    retry_lambda=lambda _: not _check_migrated_and_RTD1295(), 
                                    delay=5, max_retry=int(120/5), log=self.log.warning
                                )
                                '''
                            time.sleep(20)
                        elif ota_status in self.OTA_FAILED:
                            if ota_status == 'downloadFail' and self.resumable_test:
                                self.log.warning("Expected download failed in resumable test!")
                                time.sleep(5)
                                continue
                            if retry_times < self.MAX_RETRIES:
                                self.log.warning('OTA failed, restart otaclient and retry, {} retries left..'.
                                                 format(self.MAX_RETRIES-retry_times))
                                self.adb.executeShellCommand("stop otaclient", consoleOutput=False)
                                time.sleep(10)
                                self.adb.executeShellCommand("start otaclient", consoleOutput=False)
                                self.log.warning('Restarted otaclient, wait 120 secs and try again')
                                time.sleep(120)
                                self.timing.reset_start_time()
                                retry_times += 1
                            else:
                                self.log.error('OTA failed and reach max retries!')
                                test_result = 'Failed'
                                break
                        else:
                            self.log.warning('Unknown status, retry after 60 secs')
                            time.sleep(60)
                except Exception as e:
                    self.log.warning('The test device might be rebooting, got exception: {}'.format(repr(e)))
                    self.log.warning('Retry after 120 secs')
                    time.sleep(120)

            # If the test timeout in last step, the test_result will be empty
            if not test_result:
                self.log.error('OTA test timeout after {} secs!'.format(self.ota_timeout))
                test_result = 'Failed'

            if test_result == 'Passed' and db_change:
                migrate_result = _migrate_status()
                if not migrate_result:
                    test_result = 'Failed'

            if test_result not in ('Failed', 'Skipped'):
                self.log.info('### Step 5: Check if the device id did not change')
                # Init session to get the latest evice ID
                self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']})
                device_id_after = self.uut_owner.get_local_code_and_security_code()[0]
                self.log.warning('Device ID (After OTA): {}'.format(device_id_after))
                if device_id_before != device_id_after:
                    self.log.error('Device ID not match! Before: {}, After: {}'.format(device_id_before, device_id_after))
                    test_result = 'Failed'

        # Record failed count to raise error in after_test section
        if test_result == 'Failed':
            self.failed_count += 1
        elif test_result == 'Skipped':
            self.skipped_count += 1

        if test_result not in ('Failed', 'Skipped') and not self.start_fw.startswith('5.0'):
            self.log.info('### Step 6: Compare the MD5 checksum of existed files')
            user_id = self.uut_owner.get_user_id(escape=True)
            if self.usb_folder:
                folder_dir = self.uut_owner.get_usb_info().get('name').replace(' ', '\ ')
            else:
                folder_dir = ""

            self.NAS_FILE_MD5_DICT = self.adb.MD5_checksum(user_id, folder_dir, consoleOutput=False, timeout=1800)
            file_name_compare = _compare_filename(self.LOCAL_FILE_MD5_DICT.keys(), self.NAS_FILE_MD5_DICT.keys())
            if file_name_compare:
                self.log.info("File name comparison passed")
            else:
                self.failed_count += 1
                raise self.err.TestFailure("File name comparison failed!")

            md5_compare = _compare_checksum(self.LOCAL_FILE_MD5_DICT, self.NAS_FILE_MD5_DICT)
            if md5_compare:
                self.log.info("MD5 comparison passed")
            else:
                self.failed_count += 1
                raise self.err.TestFailure("MD5 comparison failed!")

            self.log.info('### Step 7: Try to upload a dummy file by device owner')
            with open(self.TEST_FILE, 'rb') as f:
                self.uut_owner.chuck_upload_file(file_object=f, file_name=self.TEST_FILE)
                
            user_id = self.uut_owner.get_user_id(escape=True)
            nas_md5 = self.adb.executeShellCommand('busybox md5sum /data/wd/diskVolume0/restsdk/userRoots/{0}/{1}'.
                                                    format(user_id, self.TEST_FILE), timeout=300, consoleOutput=False)[0].split()[0]
            self.log.warning("NAS MD5 Checksum: {}".format(nas_md5))

            if self.LOCAL_DUMMY_MD5 != nas_md5:
                self.failed_count += 1
                raise self.err.TestFailure('After OTA and upload a dummyfile to device, MD5 checksum comparison failed!')

            self.log.info('### Step 8: Try to download the dummy file')
            result, elapsed = self.uut_owner.search_file_by_parent_and_name(name=self.TEST_FILE, parent_id='root')
            file_id = result['id']
            content = self.uut_owner.get_file_content_v3(file_id).content
            with open('{}_download'.format(self.TEST_FILE), 'wb') as f:
                f.write(content)

            response = os.popen('md5sum {}_download'.format(self.TEST_FILE))
            if response:
                download_md5 = response.read().strip().split()[0]
            else:
                self.failed_count += 1
                raise self.err.TestFailure("Failed to get local dummy file md5 after downloaded from test device!")

            self.log.warning("Downloaded file MD5 Checksum: {}".format(download_md5))

            if self.LOCAL_DUMMY_MD5 != download_md5:
                self.failed_count += 1
                raise self.err.TestFailure("After OTA and download a dummyfile from device, MD5 checksum comparison failed!")

            self.log.info("Cleanup the dummyfiles")
            self.uut_owner.delete_file(file_id)
            os.remove('{}_download'.format(self.TEST_FILE))
        else:
            self.log.warning('Test result is in {0}, or start firmware is {0}, skip to compare the MD5 checksum steps'.format(test_result, self.start_fw))

        self.log.info("*** OTA Test Result: {} ***".format(test_result))
        # For upload test results use
        self.data.test_result['IntResult'] = test_result
        self.data.test_result['build'] = self.test_fw
        self.data.test_result['iteration'] = '{0}_itr_{1}'.format(self.test_fw, self.env.iteration)
        self.env.firmware_version = self.test_fw
        self.env.FW_BUILD = self.test_fw

    def after_loop(self):

        self.log.warning("Stop OTA client after loop to avoid device OTA in idle state")
        self.adb.stop_otaclient()
        self.log.info("*** Iterations: {}".format(self.env.iteration))
        self.log.info("*** Passed: {}".format(self.env.iteration - self.failed_count - self.skipped_count))
        self.log.info("*** Failed: {}".format(self.failed_count))
        self.log.info("*** Skipped: {}".format(self.skipped_count))

        avg_migrate_time = None
        if self.migrate_time_list:
            self.log.warning('Migration time list:')
            for index, migrate_time in enumerate(self.migrate_time_list):
                self.log.warning('Iteration {}: {}'.format(index, migrate_time))
            avg_migrate_time = np.mean(self.migrate_time_list)
            self.log.warning('*** Average migration time: {}ms'.format(avg_migrate_time))

        self.log.warning('AVG_MIGRATE_TIME={}'.format(avg_migrate_time))
        self.log.warning('MIGRATE_FROM={}'.format(self.migrate_from_version))
        self.log.warning('MIGRATE_TO={}'.format(self.migrate_to_version))
        self.log.warning('DATA_SIZE={}'.format(len(self.file_list)))
        try:
            with open('/root/app/output/db_migrate_info.txt', 'w') as f:
                f.write('AVG_MIGRATE_TIME={}\n'.format(avg_migrate_time))
                f.write('MIGRATE_FROM={}\n'.format(self.migrate_from_version))
                f.write('MIGRATE_TO={}\n'.format(self.migrate_to_version))
                f.write('DATA_SIZE={}\n'.format(len(self.file_list)))
                # Save another to_version since we cannot overwrite original jenkins env var
                f.write('TO_VERSION={}'.format(self.test_fw))
        except:
            with open('db_migrate_info.txt', 'w') as f:
                f.write('AVG_MIGRATE_TIME={}\n'.format(avg_migrate_time))
                f.write('MIGRATE_FROM={}\n'.format(self.migrate_from_version))
                f.write('MIGRATE_TO={}\n'.format(self.migrate_to_version))
                f.write('DATA_SIZE={}\n'.format(len(self.file_list)))
                f.write('TO_VERSION={}'.format(self.test_fw))

        self.log.info('*** Check the DB is not locked after {} iterations ***'.format(self.env.iteration))
        self.timing.reset_start_time()
        while not self.timing.is_timeout(60):
            curl_localHost = self.adb.executeShellCommand('curl localhost/sdk/v1/device', timeout=10)[0]
            time.sleep(1)
            if 'Connection refused' not in curl_localHost:
                self.log.info("Successfully connected to localhost")
                break
        time.sleep(30)

        # Check DB is not locked
        db_lock = self.adb.executeShellCommand("logcat -d | grep 'database is locked'")[0]
        if db_lock:
            self.failed_count += 1
            raise self.err.TestFailure('OTA stress test failed! Find database locked messages in logcat!')

        if os.path.exists(self.outputpath):
            self.log.info('Save test results to {}!!!'.format(self.outputpath))
            with open("{}/test_results.txt".format(self.outputpath), "w") as f:
                f.write('TOTAL_TEST_FAILS={}\n'.format(self.failed_count))
                f.write('TOTAL_TEST_SKIP={}\n'.format(self.skipped_count))
                f.write('TOTAL_TEST_PASS={}\n'.format(self.env.iteration - self.failed_count - self.skipped_count))

        if self.failed_count > 0:
            raise self.err.TestFailure('OTA stress test failed {0} times in {1} iterations!'.
                                       format(self.failed_count, self.env.iteration))

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** OTA stress test on Kamino Android ***
        Examples: ./start.sh integration_tests/ota_tress.py --uut_ip 10.136.137.159 --enable_auto_ota \
                  -env prod -var user -lt 500 --local_image --start_fw 4.0.1-611 --test_fw 4.1.0-711 \
                  --logstash http://10.92.234.42:8000 \
        """)
    # Test Arguments
    parser.add_argument('--test_fw', help='Update test firmware version, ex. 4.1.0-716')
    parser.add_argument('--start_fw', help='Start firmware version, ex. 4.0.1-611', default='4.0.1-611')
    parser.add_argument('--usb_folder', help='Use the data set in USB drive, if it is None then download data set from file server')
    parser.add_argument('--file_server_ip', help='File server IP address', default='fileserver.hgst.com')
    parser.add_argument('--dir_in_file_server', help='The data set dir in file server', default='/test/IOStress/')
    parser.add_argument('--private_network', action='store_true', default=False,
                        help='The test is running in private network or not, it is related to the file server')

    parser.add_argument('--local_image', action='store_true', default=False,
                        help='Download ota firmware image from local file server')
    parser.add_argument('--ota_timeout', help='The maximum ota timeout value', type=int, default=3600)
    parser.add_argument('--keep_fw_img', action='store_true', default=True, help='Keep downloaded firmware')
    parser.add_argument('--ota_bucket_id', help='Specified bucket id')
    parser.add_argument('-db', '--database_migration', action='store_true', default=False,
                        help='Database migration, will run factory reset during test')
    parser.add_argument('--disable_ota', help='Disabled OTA client after test', action='store_true')
    parser.add_argument('-rt', '--resumable_test', action='store_true', default=False, help='Run OTA resumable test, download failed is an expected error')
    parser.add_argument('-ss', '--small_size', action='store_true', default=False, help='Run OTA test on the small size diskVolume0(default 105GB)')

    test = OTAStress(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)