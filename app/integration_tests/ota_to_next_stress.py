# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import time
import re
import os
import shutil
import json

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase, Settings
from bat_scripts_new.fw_update_utility import FWUpdateUtility
from platform_libraries.cloud_api import CloudAPI

class OTAStress(FWUpdateUtility):

    TEST_SUITE = 'OTA_To_Next_Stress_Test'
    TEST_NAME = 'OTA_To_Next_Stress_Test'

    SETTINGS = Settings(**{
        'uut_owner': True,
        'disable_firmware_consistency': True
    })

    # Max retries when ota is failed
    MAX_RETRIES = 3

    # OTA update status lists
    OTA_INPROGRESS = ['downloading', 'downloaded', 'unzipping', 'unzipped',
                      'updating', 'updated', 'rebootPending', 'updateReboot',
                      'init', 'bootloaderUpdating', 'bootloaderUpdated' ]
    OTA_FAILED = ['downloadFail', 'unzipFail', 'updateFail', 'bootloaderUpdateFail', 'updateFailAfterReboot']
    OTA_COMPLETE = 'updateOk'

    # Data info for checking integrity
    LOCAL_UPLOAD_FOLDER = os.path.join(os.getcwd(), 'upload_data_before_ota')
    FILE_SERVER_PATH = '/test/IOStress'
    LOCAL_FILE_MD5_DICT = dict()
    NAS_UPLOAD_FOLDER = 'test_data_in_ota'
    NAS_FILE_MD5_DICT = dict()
    TEST_FILE = 'TEST_DB_LOCK.png'

    def init(self):
        self.failed_count = 0
        self.skipped_count = 0
        self.platform = self.adb.getModel()
        self.cloud_obj = CloudAPI(env=self.env.cloud_env)

    def before_loop(self):

        def _local_md5_checksum(path):
            response = os.popen('md5sum {}'.format(path))
            if response:
                result = response.read().strip().split()[0]
                return result
            else:
                self.log.error("There's no response from md5 checksum")
                return None

        self.log.info("[Before Loop]")
        self.log.info("Prepare local test folder")
        if os.path.exists(self.LOCAL_UPLOAD_FOLDER):
            shutil.rmtree(self.LOCAL_UPLOAD_FOLDER)
        os.mkdir(self.LOCAL_UPLOAD_FOLDER)

        self.log.info("Download test files from file server to upload folder")
        download_path = '{0}{1}'.format('ftp://ftp:ftppw@{}'.format(self.file_server_ip), self.FILE_SERVER_PATH)
        cur_dir = self.FILE_SERVER_PATH.count('/')
        cmd = 'wget --no-host-directories --cut-dirs={0} -r {1} -P {2}'.format(cur_dir, download_path, self.LOCAL_UPLOAD_FOLDER)
        if self.private_network:
            cmd += ' --no-passive'
        os.popen(cmd)

        file_list = []
        for (dirpath, dirnames, filenames) in os.walk(self.LOCAL_UPLOAD_FOLDER):
            file_list.extend(filenames)
            break

        self.log.info("Calculating the MD5 checksum, this step may take some time...")
        # Get the md5 checksum list for comparison standard
        for file in file_list:
            md5 = _local_md5_checksum(os.path.join(self.LOCAL_UPLOAD_FOLDER, file))
            if md5:
                self.LOCAL_FILE_MD5_DICT[file] = md5
            else:
                self.log.error("Failed to get MD5 checksum of file: {}".format(file))

        for index, file in enumerate(file_list):
            with open(os.path.join(self.LOCAL_UPLOAD_FOLDER, file), 'rb') as f:
                self.log.info("Uploading file: {0} into test device".format(file))
                read_data = f.read()
                self.uut_owner.upload_data(data_name=file, file_content=read_data, cleanup=True)

    def before_test(self):
        pass
        
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

        test_result = ''
        self.log.info('Step 1: Downgrade the device to {}'.format(self.start_fw))
        self.env.firmware_version = self.start_fw
        if self.adb.getFirmwareVersion() == self.start_fw:
            self.log.info('Firmware version is already {}, no need to update'.format(self.start_fw))
        else:
            try:
                super(OTAStress, self).init()
                super(OTAStress, self).before_test()
                super(OTAStress, self).test()
                self.log.info("Downgrade to {} successfully".format(self.start_fw))
            except Exception as e:
                self.log.error('Failed to downgrade the device to {0}! Error message: {1}'.format(self.start_fw, repr(e)))
                test_result = 'Skipped'

        if test_result not in ('Failed', 'Skipped'):
            self.log.info('Step 2: Record the device ID before OTA')
            self.uut_owner.init_session()
            device_id_before = self.uut_owner.get_local_code_and_security_code()[0]
            self.log.info('Device ID (Before OTA): {}'.format(device_id_before))

            self.log.info('Step 3: Wait for OTA and check update status')
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
                    self.log.warning('No device id information, wait 30 secs and retry, {} times remaining..'.format(retry_times))
                    retry_times -= 1
                    if retry_times == 0:
                        raise self.err.TestFailure('Cannot get device id!')
                    time.sleep(30)

            self.cloud_obj.register_device_in_cloud(self.platform, device_id, self.start_fw)
            result = self.cloud_obj.check_device_in_ota_bucket(bucket_id, device_id)
            if not result:
                device_id_list = []
                device_id_list.append(device_id)
                self.cloud_obj.add_device_in_ota_bucket(bucket_id, device_id_list)

            # Start ota client after checking the id is in bucket
                self.adb.start_otaclient()

            self.timing.reset_start_time()
            retry_times = 0
            restart_ota_count = 0
            while not self.timing.is_timeout(self.ota_timeout):
                try:
                    ota_status = _ota_status()
                    if not ota_status:
                        cbr = self.adb.executeShellCommand('cat /proc/device-tree/factory/cbr', consoleOutput=False)[0]
                        current_fw = self.adb.getFirmwareVersion()
                        full_ota_info = self.adb.executeShellCommand('logcat -d | grep "ota_update_status"', consoleOutput=False)[0]
                        self.log.warning('Current CBR: {}'.format(cbr))
                        self.log.warning('Current FW: {}'.format(current_fw))
                        self.log.debug('Full OTA info: {}'.format(full_ota_info))

                        if restart_ota_count % 10 == 0:
                            self.log.warning('Restart otaclient for every 10 mins')
                            self.adb.stop_otaclient()
                            time.sleep(10)
                            self.adb.start_otaclient()

                        self.timing.finish()
                        self.log.warning('[{} secs] Cannot find any ota update status info, wait for 60 secs'.
                                         format(round(float(self.timing.get_elapsed_time()), 1)))
                        restart_ota_count += 1
                        time.sleep(60)
                    else:
                        self.timing.finish()
                        self.log.info("[{0} secs] OTA status: {1}".
                                      format(round(float(self.timing.get_elapsed_time()), 1), ota_status))
                        if ota_status == self.OTA_COMPLETE:
                            self.log.info('OTA complete! Check if the firmware version is correct')
                            curr_fw = self.adb.getFirmwareVersion()
                            if curr_fw == self.test_fw:
                                test_result = 'Passed'
                            else:
                                test_result = 'Failed'
                            break
                        elif ota_status in self.OTA_INPROGRESS:
                            time.sleep(60)
                        elif ota_status in self.OTA_FAILED:
                            if retry_times < self.MAX_RETRIES:
                                self.log.warning('OTA failed, restart otaclient and retry, {} retries left..'.
                                                 format(self.MAX_RETRIES-retry_times))
                                self.adb.stop_otaclient()
                                time.sleep(10)
                                self.adb.start_otaclient()
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

            self.log.info('Step 4: Check if the device id did not change')
            self.uut_owner.init_session()
            device_id_after = self.uut_owner.get_local_code_and_security_code()[0]
            self.log.info('Device ID (After OTA): {}'.format(device_id_after))
            if device_id_before != device_id_after:
                self.log.error('Device ID not match! Before: {}, After: {}'.format(device_id_before, device_id_after))
                test_result = 'Failed'

        # Record failed count to raise error in after_test section
        if test_result == 'Failed':
            self.failed_count += 1
        elif test_result == 'Skipped':
            self.skipped_count += 1

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

        if test_result not in ('Failed', 'Skipped'):
            self.log.info('Step 5: Compare the MD5 checksum of existed files')
            user_id = self.uut_owner.get_user_id(escape=True)
            self.NAS_FILE_MD5_DICT = self.adb.MD5_checksum(user_id, "")
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

        self.log.info("*** OTA Test Result: {} ***".format(test_result))
        self.data.test_result['IntResult'] = test_result

    def after_loop(self):

        def _create_random_file(file_name, local_path='', file_size='1048576'):
            # Default 1MB dummy file
            self.log.info('Creating file: {}'.format(file_name))
            try:
                with open(os.path.join(local_path, file_name), 'wb') as f:
                    f.write(os.urandom(int(file_size)))
            except Exception as e:
                self.log.error('Failed to create file: {0}, error message: {1}'.format(local_path, repr(e)))
                raise

        self.log.info("*** Iterations: {}".format(self.env.iteration))
        self.log.info("*** Passed: {}".format(self.env.iteration - self.failed_count - self.skipped_count))
        self.log.info("*** Failed: {}".format(self.failed_count))
        self.log.info("*** Skipped: {}".format(self.skipped_count))

        self.log.info('*** Check the DB is not locked after {} iterations'.format(self.env.iteration))

        self.timing.reset_start_time()
        while not self.timing.is_timeout(60):
            curl_localHost = self.adb.executeShellCommand('curl localhost/sdk/v1/device', timeout=10)[0]
            time.sleep(1)
            if 'Connection refused' not in curl_localHost:
                self.log.info("Successfully connected to localhost")
                break
        time.sleep(30)

        # Check DB is not locked
        db_lock = self.adb.executeShellCommand("logcat -d | grep 'database table is locked'")[0]
        self.log.debug(db_lock)
        if db_lock:
            raise self.err.TestFailure('OTA stress test failed! Find database locked messages in logcat!')

        self.log.info('Try to upload a new file by device owner')
        _create_random_file(self.TEST_FILE)
        self.uut_owner.upload_data(self.TEST_FILE)
        user_id = self.uut_owner.get_user_id(escape=True)
        if self.adb.check_file_exist_in_nas("{}".format(self.TEST_FILE), user_id):
            self.log.info('Upload test file to device successfully!')
        else:
            raise self.err.TestFailure('OTA stress test failed! Cannot find test file in device!')

        if self.failed_count > 0:
            raise self.err.TestFailure('OTA stress test failed {0} times in {1} iterations!'.
                                       format(self.failed_count, self.env.iteration))

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** OTA stress test on Kamino Android ***
        Examples: ./start.sh integration_tests/ota_to_next_stress.py --uut_ip 10.136.137.159\
                  -env prod -var user -lt 500 --local_image --start_fw 4.1.0-725 --test_fw 4.1.0-726 \
                  --logstash http://10.92.234.42:8000 \
        """)
    # Test Arguments
    parser.add_argument('--test_fw', help='Update test firmware version, ex. 4.1.0-726')
    parser.add_argument('--start_fw', help='Start firmware version, ex. 4.0.1-725')
    parser.add_argument('--file_server_ip', help='File server IP address', default='fileserver.hgst.com')
    parser.add_argument('--local_image', action='store_true', default=False,
                        help='Download ota firmware image from local file server')
    parser.add_argument('--ota_timeout', help='The maximum ota timeout value', default=3600)
    parser.add_argument('--keep_fw_img', action='store_true', default=True, help='Keep downloaded firmware')
    parser.add_argument('--private_network', action='store_true', default=False,
                        help='The test is running in private network or not')
    parser.add_argument('--ota_bucket_id', help='Specified bucket id')

    test = OTAStress(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)