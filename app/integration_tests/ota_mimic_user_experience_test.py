# -*- coding: utf-8 -*-

__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time
import re
import os
import json
import string
import numpy as np


# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.cloud_api import CloudAPI
from jenkins_scripts.update_bucket import OTABucket

class OTAUserMimicTest(TestCase):

    TEST_SUITE = 'OTA Test'
    TEST_NAME = 'OTA_User_Mimic_Test'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-36322'
    PRIORITY = 'Critical'
    COMPONENT = 'OTA CLIENT'
    ISSUE_JIRA_ID = None
    REPORT_NAME = 'OTA'

    SETTINGS = {
        'uut_owner': True,
        'disable_firmware_consistency': True,
        'enable_auto_ota': True
    }

    # OTA update status lists
    OTA_INPROGRESS = ['downloading', 'downloaded', 'unzipping', 'unzipped',
                      'updating', 'updated', 'rebootPending', 'updateReboot',
                      'init', 'bootloaderUpdating', 'bootloaderUpdated' ]
    OTA_FAILED = ['downloadFail', 'unzipFail', 'updateFail', 'bootloaderUpdateFail', 'updateFailAfterReboot']
    OTA_COMPLETE = 'updateOk'

    def declare(self):
        self.file_server_ip = 'fileserver.hgst.com'
        self.dir_in_file_server = '/test/IOStress'

    def init(self):
        self.platform = self.adb.getModel()
        self.cloud_obj = CloudAPI(env=self.env.cloud_env)
        # Data info for checking integrity
        self.LOCAL_UPLOAD_FOLDER = os.path.join(os.getcwd(), '{}'.format(self.dir_in_file_server.split('/')[-1]))
        self.FILE_LIST = []
        self.LOCAL_FILE_MD5_DICT = dict()
        self.NAS_FILE_MD5_DICT = dict()
        # Dummyfile used for upload/download file after each iteration
        self.LOCAL_DUMMY_MD5 = ""
        self.TEST_FILE = 'dummyfile'

    def before_test(self):

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

        self.log.info("[Before Test]")
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
                OTA_BUCKET.update_bucket()
                bucket_to_version = OTA_BUCKET.get_ota_specific_buckets_info()['to_version']
                self.log.warning("Double check bucket new to_version is: {}".format(bucket_to_version))
                if self.test_fw != bucket_to_version:
                    raise self.err.TestFailure("Failed to update bucket to specified version! Stop the test!")
            else:
                self.log.warning("Test version matches the to_version in bucket, keep testing ...")

        if self.test_with_dataset:
            # Upload folder prepare
            self.log.info("*** Prepare local test folder ***")
            self.log.info('Download test files from file server to {}...'.format(self.LOCAL_UPLOAD_FOLDER))
            download_path = '{0}{1}'.format('http://{}/'.format(self.file_server_ip), self.dir_in_file_server)
            cur_dir = self.dir_in_file_server.count('/')
            cmd = "wget -q -N -nH --no-parent --reject='index.html*' --no-host-directories --cut-dirs={0} -r {1}/".format(cur_dir, download_path)
            self.log.info("Download files from server:'{0}'".format(download_path))
            self.log.info('Execute command: {}'.format(cmd))
            os.popen(cmd)
            self.log.info('Download successfully.')
            for (dirpath, dirnames, filenames) in os.walk(self.LOCAL_UPLOAD_FOLDER):
                self.FILE_LIST.extend(filenames)
                break
            self.log.info('DATA_SIZE={}'.format(len(self.FILE_LIST)))
            self.log.info('Local upload test folders are ready')
            self.log.info("Calculating the MD5 checksum, this step may take some time...")
            # Get the md5 checksum list for comparison standard
            for file in self.FILE_LIST:
                md5 = _local_md5_checksum(os.path.join(self.LOCAL_UPLOAD_FOLDER, file))
                if md5:
                    self.LOCAL_FILE_MD5_DICT[file] = md5
                else:
                    self.log.error("Failed to get MD5 checksum of file: {}".format(file))
        if self.change_ota_interval_time:
            self.action_to_change_ota_interval_time(self.change_ota_interval_time)

        # Dummyfile used for upload/download file after each iteration
        _create_random_file(self.TEST_FILE)
        self.LOCAL_DUMMY_MD5 = _local_md5_checksum(self.TEST_FILE)
        if not self.LOCAL_DUMMY_MD5:
            raise self.err.TestFailure('Failed to get the local dummy md5 checksum!')
        self.log.warning("Local dummyfile MD5 Checksum: {}".format(self.LOCAL_DUMMY_MD5))

        # Get device mac address
        self.log.info('Get device mac address ...')
        if self.platform == 'monarch' or self.platform == 'pelican':
            self.mac_address = self.adb.get_mac_address(interface='eth0')
        if self.platform == 'yoda' or self.platform == 'yodaplus':
            self.mac_address = self.adb.get_mac_address(interface='wlan0')

    def test(self):

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

        def _upload_data():
            self.log.info('Start to upload test files to device ...')
            for index, file in enumerate(self.FILE_LIST):
                with open(os.path.join(self.LOCAL_UPLOAD_FOLDER, file), 'rb') as f:
                    self.log.info('Uploading file: {0} to device.'.format(file))
                    self.uut_owner.chuck_upload_file(file_object=f, file_name=file)
            self.log.info('Upload files finished')

        def _migrate_status():
            migrate_info = self.adb.executeShellCommand('logcat -d | grep "migrated" | grep "Migrate" | grep -v "MigratedLocal"',
                                                        consoleOutput=False)[0].strip()
            if not migrate_info:
                raise self.err.TestFailure("Cannot find migration information, test failed!")

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
            self.migrate_from_version = migrate_from
            self.migrate_to_version = migrate_to

        self.log.info('### Record the device ID and upload some data before OTA ...')
        self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']})
        self.device_id_before = self.uut_owner.get_local_code_and_security_code()[0]
        self.log.warning('Device ID (Before OTA): {}'.format(self.device_id_before))
        _upload_data()

        self.log.info('### Wait for OTA and check update status')
        self.log.info('Checking if device id has been added in OTA bucket or not ...')
        if self.ota_bucket_id != "":
            self.log.info("Specified ota_bucket_id:{}".format(self.ota_bucket_id))
            bucket_id = self.ota_bucket_id
        else:
            self.log.info("Checking the bucket id from cloud server ...")
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
                    'No device id information, wait 10 secs and retry, {} times remaining..'.format(retry_times))
                retry_times -= 1
                if retry_times == 0:
                    raise self.err.TestFailure('Cannot get device_id in device locally!!')
                time.sleep(10)

        result = self.cloud_obj.check_device_in_ota_bucket(bucket_id, device_id, self.adb)
        if not result:
            device_id_list = []
            device_id_list.append(device_id)
            self.cloud_obj.add_device_in_ota_bucket(bucket_id, device_id_list)

        # Check otaclient service is enabled on the device
        otaclient_daemon = self.adb.executeShellCommand('ps | grep otaclient')[0]
        if 'otaclient' not in otaclient_daemon:
            self.log.warning('****** otaclient service is not running in currently device, start the otaclient service forcibly!!!　******')
            self.adb.executeShellCommand("start otaclient")
        # Check ota.lock property is set to 0, usually are not have this ota.lock property. If the property is set to 1, change it to 0.
        ota_lock = self.adb.executeShellCommand('getprop persist.wd.ota.lock')[0]
        if '1' in ota_lock:
            self.adb.start_otaclient()
        # Remove ota_lock files if needed
        lock_file_status = self.adb.executeShellCommand("ls | /tmp/ota_lock")[0]
        self.log.warning("Lock file status: {}".format(lock_file_status))
        if lock_file_status != "":
            self.adb.executeShellCommand("rm /tmp/ota_lock")

        self.timing.reset_start_time()
        retry_times = 0
        wait_ota_count = 0
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

                    if wait_ota_count >= 80:
                        self.log.info('Already retry more than 20 mins, sometimes the "updateOK" will not be in logcat, compare the version directly')
                        if current_fw == self.test_fw:
                            self.log.info('Current FW is matched with testing FW, check point passed!!')
                            break
                        else:
                            if current_fw:
                                current_fw_prefix = current_fw.split('-')[0]
                                current_fw_suffix = current_fw.split('-')[1]
                                if current_fw_prefix == expect_fw_prefix and int(current_fw_suffix) > int(expect_fw_suffix):
                                    self.log.warning("Current firmware is newer then expect version,\
                                                      mark the test as Passed but need to check if bucket to_version is changed")
                                    break
                        self.log.info("Firmware version not match, keep retrying...")
                    
                    self.timing.finish()
                    self.log.warning('[{} secs] Cannot find any ota update status info, wait for 15 secs'.
                                     format(round(self.timing.get_elapsed_time(), 1)))
                    wait_ota_count += 1
                    time.sleep(15)
                else:
                    self.timing.finish()
                    self.log.info("[{0} secs] OTA status: {1}".
                                  format(round(self.timing.get_elapsed_time(), 1), ota_status))
                    if ota_status == self.OTA_COMPLETE:
                        self.log.info('OTA completed! Check if the firmware version is correct')
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
                                self.log.info('Current FW, testing FW and Wiri FW are matched, Check Wiri FW passed')
                                break
                            if self.timing.is_timeout(60*3):
                                raise self.err.TestFailure("Firmware version not match! Expect: {}, Current: {}, Wiri: {}".format(self.test_fw, curr_fw, wiri_fw))
                        else:
                            self.log.info('Current FW, testing FW and Wiri FW are matched, Check Wiri FW passed')
                            break
                    elif ota_status in self.OTA_INPROGRESS:
                        if (ota_status == 'updating' or ota_status == 'updateReboot'):
                            self.log.warning('Device OTA STATUS is in {}, wait for device to shutdown ...'.format(ota_status))
                            if not self.adb.wait_for_device_to_shutdown(timeout=60*10): # Wait max 10 mins to let device updating(flash) firmware image
                                self.log.error('Reboot device: FAILED.')
                                raise self.err.TestFailure('Reboot device failed')
                            self.log.info('Reboot device: PASSED.')
                            self.log.info('Start to wait for device boot completed...')
                            if not self.adb.wait_for_device_boot_completed(timeout=60*10, disable_ota=False):
                                self.log.error('Device seems down.')
                                raise self.err.TestFailure('Timeout({}secs) to wait device boot completed..'.format(self.timeout))
                        else:
                            self.log.warning('OTA STATUS is in update progress: {}, keep waiting the OTA progress ...'.format(ota_status))
                        time.sleep(20) # Waiting time during next ota steps check interval
                    elif ota_status in self.OTA_FAILED:
                        if ota_status == 'downloadFail' and self.resumable_test:
                            self.log.warning("Expected download failed in resumable test!")
                            time.sleep(5)
                            continue
                        if retry_times < self.MAX_RETRIES:
                            self.log.warning('Wait 2 mins and try again')
                            time.sleep(60*2)
                            self.timing.reset_start_time()
                            retry_times += 1
                        else:
                            self.err.TestFailure('OTA failed and reach max retries!')
                            break
                    else:
                        self.log.warning('Unknown status, retry after 60 secs')
                        time.sleep(60)
            except Exception as e:
                self.log.warning('The test device might be rebooting, got exception: {}'.format(repr(e)))
                self.log.warning('Retry after 120 secs')
                time.sleep(120)

        if self.database_migration: #TODO: Currently need to provide the db change value, need to get by script itself later
            migrate_result = _migrate_status()

        # Check DB is not locked after OTA
        self.check_restsdk_service()
        # Check device_id is the same after OTA
        self.check_device_id_after_OTA()
        # Check device can upload download files successfully after OTA
        self.check_device_RW_via_restsdk_request_after_OTA()
        if self.test_with_dataset:
            self.check_md5_for_existed_files()
        # Check ota path is original downloadDir
        self.check_ota_download_path()
        self.check_proxy_portforward_connection()
        self.log.info("******** All check point passed!! OTA Test PASSED !!! ********")

    def after_test(self):
        if self.disable_ota_after_test:
            self.log.warning("Stop OTA client after test")
            self.adb.stop_otaclient()

        if self.database_migration:
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
                self.log.warning('DATA_SIZE={}'.format(len(self.FILE_LIST)))

    def check_md5_for_existed_files(self):

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

        self.log.info('### Start to compare the MD5 checksum of existed files ...')
        user_id = self.uut_owner.get_user_id(escape=True)
        folder_dir = ""

        self.NAS_FILE_MD5_DICT = self.adb.MD5_checksum(user_id, folder_dir, consoleOutput=False, timeout=60*30)
        file_name_compare = _compare_filename(self.LOCAL_FILE_MD5_DICT.keys(), self.NAS_FILE_MD5_DICT.keys())
        if file_name_compare:
            self.log.info("File name comparison passed")
        else:
            raise self.err.TestFailure("File name comparison failed!")

        md5_compare = _compare_checksum(self.LOCAL_FILE_MD5_DICT, self.NAS_FILE_MD5_DICT)
        if md5_compare:
            self.log.info("MD5 comparison passed")
        else:
            raise self.err.TestFailure("MD5 comparison failed!")

    def check_device_RW_via_restsdk_request_after_OTA(self):
        self.log.info('### Try to upload a dummy file by device owner ...')
        with open(self.TEST_FILE, 'rb') as f:
            self.uut_owner.chuck_upload_file(file_object=f, file_name=self.TEST_FILE)
        user_id = self.uut_owner.get_user_id(escape=True)
        nas_md5 = self.adb.executeShellCommand('busybox md5sum /data/wd/diskVolume0/restsdk/userRoots/{0}/{1}'.
                                                format(user_id, self.TEST_FILE), timeout=300, consoleOutput=False)[0].split()[0]
        self.log.warning("NAS MD5 Checksum: {}".format(nas_md5))

        if self.LOCAL_DUMMY_MD5 != nas_md5:
            raise self.err.TestFailure('After OTA and upload a dummyfile to device, MD5 checksum comparison failed!')

        self.log.info('### Try to download the dummy file ...')
        result, elapsed = self.uut_owner.search_file_by_parent_and_name(name=self.TEST_FILE, parent_id='root')
        file_id = result['id']
        content = self.uut_owner.get_file_content_v3(file_id).content
        with open('{}_download'.format(self.TEST_FILE), 'wb') as f:
            f.write(content)

        response = os.popen('md5sum {}_download'.format(self.TEST_FILE))
        if response:
            download_md5 = response.read().strip().split()[0]
        else:
            raise self.err.TestFailure("Failed to get local dummy file md5 after downloaded from test device!")
        self.log.warning("Downloaded file MD5 Checksum: {}".format(download_md5))
        if self.LOCAL_DUMMY_MD5 != download_md5:
            raise self.err.TestFailure("After OTA and download a dummyfile from device, MD5 checksum comparison failed!")

        self.log.info("Cleanup the dummyfiles")
        self.uut_owner.delete_file(file_id)
        os.remove('{}_download'.format(self.TEST_FILE))

    def check_device_id_after_OTA(self):
        self.log.info('### Check device id after ...')
        # Init session to get the latest device ID
        self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']})
        self.device_id_after = self.uut_owner.get_local_code_and_security_code()[0]
        self.log.warning('Print out Device ID after OTA: {}'.format(self.device_id_after))
        if self.device_id_before == self.device_id_after:
            self.log.info('Device ID is match.')
        else:
            raise self.err.TestFailure('Device ID is not matched, Before: {0}, After: {1}, OTA test failed !!!'
                .format(self.device_id_before, self.device_id_after))

    def check_restsdk_service(self):
        self.log.info('### Check restsdk service can get device info locally ...')
        self.timing.reset_start_time()
        while not self.timing.is_timeout(60*3):
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
        self.timing.reset_start_time()
        while not self.timing.is_timeout(60*2):
            # Execute sdk/v1/device command to check device info to confirm restsdk service running properly
            curl_localHost = self.adb.executeShellCommand('curl localhost/sdk/v1/device?pretty=true')[0]
            if 'Connection refused' in curl_localHost:
                self.log.warning('Connection refused happened, wait for 5 secs and try again...')
                time.sleep(5)
            else:
                break
        else:
            raise self.err.TestFailure("Connected to localhost failed after retry for 2 mins ...")

    def check_ota_download_path(self):
        check_path = self.adb.executeShellCommand('logcat -d -s otaclient | grep ota_start')[0]
        if '/tmp/otaclient/fwupdate' not in check_path:
            self.log.warning('logs: {}'.format(check_path))
            raise self.err.TestFailure("ota imagePath has been changed, not original downloadDir !!")

    def check_proxy_portforward_connection(self):
        proxy_url = self.cloud_obj.get_device_info_with_device_id(device_id=self.device_id_after)['network']['proxyURL']
        self.log.info('Device proxy url: {}'.format(proxy_url))
        if not self.cloud_obj.get_device_id_from_proxy_portforward_url_connection(proxy_url):
            raise self.err.TestFailure('Failed to get device id from proxy url connection')
        try:
            port_forward_url = self.cloud_obj.get_device_info_with_device_id(device_id=self.device_id_after)['network']['portForwardURL']
            if not self.cloud_obj.get_device_id_from_proxy_portforward_url_connection(port_forward_url):
                raise self.err.TestFailure('Failed to get device id from port_forward url connection')
        except KeyError:
            self.log.warning('Device is not enabled the port forward, skip the portForwardURL check')

    def action_to_change_ota_interval_time(self, ota_interval_time):
        self.log.warning('***** Change ota interval time to {} secs, this action will restart otaclient service *****'.format(ota_interval_time))
        self.adb.executeShellCommand('mount -o remount,rw /system')
        self.adb.executeShellCommand("busybox sed -i -- 's/otaCheckInterval = 21600/otaCheckInterval = {}/g' /system/etc/otaclient.toml"
            .format(str(ota_interval_time)))
        self.adb.executeShellCommand("stop otaclient")
        self.adb.executeShellCommand("start otaclient")


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** OTA User Mimic test ***
        Examples: ./start.sh integration_tests/ota_mimic_user_experience_test.py --uut_ip 10.200.140.120 
        -env qa1 --test_fw 7.9.0-129 --ota_bucket_id d02d6520-cbb0-11ea-acce-d1fc87421926 --test_with_dataset\
        """)
    # Test Arguments
    parser.add_argument('--test_fw', help='Update test firmware version, ex. 7.9.0-129')
    parser.add_argument('--ota_timeout', help='The maximum ota timeout value, default is 1 hour', type=int, default=60*60)
    parser.add_argument('--ota_bucket_id', help='Specified bucket id')
    parser.add_argument('-rt', '--resumable_test', action='store_true', default=False, help='Run OTA resumable test, download failed is an expected error')
    parser.add_argument('-db', '--database_migration', action='store_true', default=False, help='Database migration will run when restsdk database changed')
    parser.add_argument('--disable_ota_after_test', help='Disabled OTA client after test', default=False, action='store_true')
    parser.add_argument('--test_with_dataset', help='Upload dataset on the device to test the OTA', default=False, action='store_true')
    parser.add_argument('--file_server_ip', help='File server IP address', default='fileserver.hgst.com')
    parser.add_argument('--dir_in_file_server', help='The data set dir in file server', default='/test/IOStress')
    parser.add_argument('--change_ota_interval_time', help='Changed ota interval time default time to given value', default=None)

    test = OTAUserMimicTest(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)