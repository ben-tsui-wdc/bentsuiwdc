# -*- coding: utf-8 -*-
""" Test case to run OTA update by nasAdmin API
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
import os
import shutil
import datetime
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from godzilla_scripts.bat_scripts.firmware_update import FirmwareUpdate
from platform_libraries.cloud_api import CloudAPI
from platform_libraries.constants import Godzilla as GZA


class OTAUpdateNow(GodzillaTestCase):

    TEST_SUITE = 'Platform Functional Tests'
    TEST_NAME = 'OTA API Test'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-6937,GZA-6938,GZA-6939,GZA-8604'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    REPORT_NAME = 'OTA API'

    def declare(self):
        self.file_server_ip = "10.200.141.26"
        self.local_image = False
        self.ota_timeout = 7200
        self.ota_retry_delay = 5
        self.keep_fw_img = False
        self.ota_bucket_id = "default"
        self.update_mode = "now"
        self.dir_in_file_server = "/test/IOStress/"
        self.share_folder_name = "ota_data"
        self.special_dataset = None
        self.skip_data_integrity = False

    def init(self):
        # test fw version will be fetched from cloud info
        self.test_fw = None
        self.local_upload_folder = os.path.join(os.getcwd(), 'upload_data_before_ota')
        self.share_folder_name = "{0}_update_{1}".format(self.share_folder_name, self.update_mode)
        if self.update_mode == "n_plus_one":
            self.TEST_JIRA_ID = 'GZA-6953'
        self.update_process_timeout = 900
        # for db migration metrics
        self.restsdk_indexing_elapsed_time = None
        self.db_time_total = 0
        self.db_from_overall = None
        self.db_to_overall = None
        self.rebuild_fts = False

    def before_loop(self):
        if not self.special_dataset:
            # Data info for checking integrity
            self.log.info("Prepare local test folder")
            if os.path.exists(self.local_upload_folder):
                shutil.rmtree(self.local_upload_folder)
            os.mkdir(self.local_upload_folder)

    def test(self):
        if self.update_mode == "n_plus_one":
            # N+1 use the final version at the beginning, and fake the firmware version in step 4
            _start_fw = self.env.firmware_version
        else:
            _start_fw = self.start_fw
        self.log.info("Step 1: Downgrade the firmware to {}".format(_start_fw))
        self.downgrade_firmware(_start_fw)

        self.log.info("Step 2: Prepare the test dataset for indexing and db mibration")
        if self.skip_data_integrity:
            self.log.info("Data integrity check is skipped.")
        else:
            if self.special_dataset:
                self.log.info("Use existed dataset in share folder: {}".format(self.special_dataset))
            else:
                self.log.info("Download test dataset from the file server to the upload folder")
                self.download_test_dataset()

        self.log.info("Step 3: Create RestSDK filesystem and wait for the indexing process complete")
        if self.skip_data_integrity:
            self.log.info("Data integrity check is skipped.")
        else:
            self.create_restsdk_filesystem_and_run_indexing()

        self.log.info("Step 4: Add device in the OTA bucket. If it's N+1 test, modify the fw version to the older one")
        if self.ota_bucket_id == "default":
            self.ota_bucket_id = GZA.DEVICE_INFO.get(self.env.model).get("ota_default_bucket_v2_{}".format(self.env.cloud_env))
        elif self.ota_bucket_id == "special":
            self.ota_bucket_id = GZA.DEVICE_INFO.get(self.env.model).get("ota_special_bucket_v2_{}".format(self.env.cloud_env))

        if not self.ota_bucket_id:
            raise self.err.StopTest('No OTA bucket id is specified or cannot find it in constant file!')
        else:
            self.add_device_in_specific_bucket()

        if self.update_mode == "n_plus_one":
            self.ssh_client.execute('echo "{}" > /etc/version'.format(self.start_fw))

        # Note: We need to restart otaclient after this step, but it's already included in the step 5

        self.log.info("Step 5: Check the OTA schedule and configure the test environment")
        self.setup_ota_schedule()

        self.log.info("Step 6: Start running the OTA test")
        self.trigger_ota()

        self.log.info("Step 7: Check if the DB migration happened and calculate the time")
        if self.skip_data_integrity:
            self.log.info("Data integrity check is skipped.")
        else:
            self.check_db_migration()

        self.log.info("Step 8: Compare the checksum of dataset before and after the OTA")
        if self.skip_data_integrity:
            self.log.info("Data integrity check is skipped.")
        else:
            self.compare_dataset_checksum()

    def after_test(self):
        if self.update_mode in ("daily", "weekly"):
            self.log.info("Enable the NTP service again after testing")
            self.ssh_client.update_ntp_status(status="on")
            self.log.info("Change the OTA update mode to random after testing")
            self.ssh_client.ota_change_auto_update(mode="enabled")

        self.log.info("===== Test Result =====")
        self.log.info("FW_TO_VERSION={}".format(self.test_fw))
        self.log.info("RESTSDK_INDEXING_TIME={}".format(self.restsdk_indexing_elapsed_time))
        self.log.info("DB_MIGRATION_TIME={}".format(self.db_time_total))
        self.log.info("DB_MIGRATION_FROM={}".format(self.db_from_overall))
        self.log.info("DB_MIGRATION_TO={}".format(self.db_to_overall))
        if self.rebuild_fts:
            self.log.info("FTS_REBUILD_TIME={}".format(self.rebuild_fts_time))
        # Restore test fw value for next iteration
        self.test_fw = None

    def after_loop(self):
        if not self.special_dataset:
            if os.path.exists(self.local_upload_folder):
                self.log.info("Delete local test folder after testing")
                shutil.rmtree(self.local_upload_folder)

    def downgrade_firmware(self, fw_version):
        self.env_dict = self.env.dump_to_dict()
        firmware_update = FirmwareUpdate(self.env_dict)
        firmware_update.fw_version = fw_version
        firmware_update.keep_fw_img = self.keep_fw_img
        firmware_update.local_image = self.local_image
        firmware_update.force_update = True
        firmware_update.before_test()
        firmware_update.test()
        firmware_update.after_test()

    def download_test_dataset(self):
        download_path = '{0}{1}'.format('ftp://ftp:ftppw@{}'.format(self.file_server_ip), self.dir_in_file_server)
        cur_dir = self.dir_in_file_server.count('/')
        cmd = 'wget --no-host-directories --cut-dirs={0} -r {1} -P {2} -N --no-passive'. \
            format(cur_dir, download_path, self.local_upload_folder)
        os.popen(cmd)

        self.file_list = []
        for (dirpath, dirnames, filenames) in os.walk(self.local_upload_folder):
            self.file_list.extend(filenames)
            break

        self.ssh_client.create_share(self.share_folder_name, public=True)
        self.ssh_client.sftp_connect()
        for file in self.file_list:
            self.log.info("Uploading file: {0} into test device".format(file))
            self.ssh_client.sftp_upload(os.path.join(self.local_upload_folder, file),
                                        "/shares/{0}/{1}".format(self.share_folder_name, file))
        self.ssh_client.sftp_close()
        self.folder_md5_before = self.ssh_client.get_folder_md5_checksum("/shares/{}".format(self.share_folder_name))
        self.log.info("Test data folder MD5 (before): {}".format(self.folder_md5_before))

    def create_restsdk_filesystem_and_run_indexing(self):
        if self.special_dataset:
            folder_path = "/mnt/HD/HD_a2/{}".format(self.special_dataset)
        else:
            folder_path = "/mnt/HD/HD_a2/{}".format(self.share_folder_name)

        self.uut_owner.init_session()
        create_fs_retries = 3
        create_fs_counts = 0
        while True:
            try:
                self.filesystem_id = self.uut_owner.create_filesystem(folder_path=folder_path, name=folder_path)
                break
            except Exception as e:
                if create_fs_counts >= create_fs_retries:
                    raise self.err.StopTest('Create filesystem failed and reaches max retries, stop the test!')

                self.log.warning("Failed to create filesystem, error messages: {}, retry after 60 secs".format(repr(e)))
                time.sleep(60)
                create_fs_counts += 1
                continue

        self.log.info('Wait for indexing complete by REST SDK call...')
        start_time = time.time()
        filesystem = None
        max_waiting_time = 60 * 60 * 24 * 14  # 14 days
        restsdk_indexing_check_interval = 5
        while time.time() - start_time < max_waiting_time:
            filesystem = self.uut_owner.get_filesystem(self.filesystem_id)
            if filesystem and 'stats' in filesystem:
                scan_status = filesystem.get('stats').get('firstScanStatus')
                scan_progress = filesystem.get('stats').get('firstScanProgress')
                self.log.info("Indexing status: {0}, progress: {1}".format(scan_status, scan_progress))
                if scan_status == 'complete':
                    start_time = filesystem.get('stats').get('firstScanStart')
                    end_time = filesystem.get('stats').get('firstScanEnd')
                    self.restsdk_indexing_elapsed_time = self.calculate_indexing_elapsed_time(start_time, end_time)
                    break
            else:
                self.log.warning('Cannot find restsdk indexing info, result: {}, keep waiting...'.format(filesystem))
            if restsdk_indexing_check_interval != 60 and time.time() - start_time > 60 * 5:
                self.log.info("RestSDK indexing takes longer than 5 mins, change the check interval to 60 secs")
                restsdk_indexing_check_interval = 60
            time.sleep(restsdk_indexing_check_interval)
        if filesystem:
            self.log.warning('Last filesystem info: {}'.format(filesystem))
            if filesystem.get('stats').get('firstScanStatus') != 'complete':
                raise self.err.StopTest('Indexing is still not complete after {} secs'.format(max_waiting_time))

    def add_device_in_specific_bucket(self):
        self.log.info("Adding device to the specific bucket: {}".format(self.ota_bucket_id))
        self.device_id = self.uut_owner.get_local_code_and_security_code(without_auth=True)[0]
        self.cloud = CloudAPI(env=self.env.cloud_env)
        self.cloud.add_device_in_ota_bucket(self.ota_bucket_id, [self.device_id])

    def setup_ota_schedule(self):
        self.ssh_client.connect()
        self.ssh_client.restart_otaclient()
        if self.update_mode in ("daily", "weekly"):
            self.log.info("The update mode is {}, disable the NTP and update the device time".
                          format(self.update_mode))
            # default date: 091421552020.00 (Mon Sep 14 21:55:00 PDT 2020)
            self.ssh_client.update_ntp_status(status="off")
            self.ssh_client.update_device_date()
        if self.update_mode == "daily":
            self.log.info("Set the OTA update mode to daily, 22:00")
            self.ssh_client.ota_change_auto_update(mode="scheduled", schedule={"day": "everyday", "hour": 22})
        elif self.update_mode == "weekly":
            self.log.info("Set the OTA update mode to weekly (Monday), 22:00")
            self.ssh_client.ota_change_auto_update(mode="scheduled", schedule={"day": "monday", "hour": 22})
        else:
            self.log.info("Set the OTA update mode to random")
            self.ssh_client.ota_change_auto_update(mode="enabled")

    def trigger_ota(self):
        self.log.info("OTA timeout = {} seconds".format(self.ota_timeout))
        self.log.info("OTA retry delay = {} seconds".format(self.ota_retry_delay))
        restart_otaclient_count = 0
        update_status = None
        start_to_update = False
        self.ota_start_time = time.time()
        while True:
            if self.check_timeout(self.ota_start_time, self.ota_timeout):
                raise self.err.TestFailure('OTA reaches the timeout and still not update succussfully! '
                                           'The last update status: {}'.format(update_status))
            try:
                result = self.ssh_client.get_ota_update_status()
            except Exception:
                self.log.warning("Get ota status failed, the device might in reboot process, try again in {} seconds!".
                                 format(self.ota_retry_delay))
                time.sleep(self.ota_retry_delay)
                continue
            update_status = result.get('updateStatus')
            current_version = result.get('version')
            self.log.warning("OTA status: {}".format(update_status))
            if update_status == "updateAvailable":  # GZA-6938: Check available update with older version
                if not self.test_fw:
                    self.test_fw = result.get('available')
                    if self.update_mode in ("now", "n_plus_one"):
                        self.log.info("Update the OTA right now by calling the OTA API")
                        self.ssh_client.ota_update_firmware_now()
                        self.log.info("OTA start running, current_version: {0}, available_version: {1}".
                                      format(current_version, self.test_fw))
                    elif self.update_mode == "random":
                        self.log.info("The update mode is random, change the interval to 60 secs in ota config file")
                        self.ssh_client.update_ota_interval(interval=60)
                    else:
                        update_policy = self.ssh_client.execute("cat /var/log/otaclient.log | grep updatePolicy")[0]
                        if update_policy:
                            self.log.warning("Update Policy: {}".format(update_policy))
                else:
                    self.log.info("Keep waiting for the OTA, elapsed time: {} sec".
                                  format(int(time.time()-self.ota_start_time)))
            elif update_status == "downloading":
                if not self.test_fw:
                    self.test_fw = result.get('available')
                percentage = result.get('downloadPercent')
                if percentage:
                    self.log.info("Progress: {}%".format(int(percentage)))
            elif update_status == "downloadFail":
                self.log.info("Download failed, wait for 60 secs and trigger the OTA again")
                time.sleep(60)
                self.ssh_client.ota_update_firmware_now()
            elif update_status == "updateReboot":
                if not self.test_fw:
                    self.test_fw = result.get('available')
                self.ssh_client.wait_for_device_to_shutdown()
                self.ssh_client.wait_for_device_boot_completed()
            elif update_status == "updating":
                if not start_to_update:
                    if not self.test_fw:
                        self.test_fw = result.get('available')
                    self.log.info("Enter updating status, reset the start time and change max timeout to {}".
                                  format(self.update_process_timeout))
                    self.ota_start_time = time.time()
                    self.ota_timeout = self.update_process_timeout
                    self.log.info("Change the check ota interval to 5 secs")
                    self.ota_retry_delay = 5
                    start_to_update = True
            elif update_status == "noUpdate":  # GZA-6937: Check available update with latest version by OTA API
                if not self.test_fw:
                    """
                    if self.test_fw is none, that means the status was never changed to updateAvailable 
                    or started running the OTA, need to wait for the cloud to be updated
                    """
                    self.log.info("Waiting for the cloud to update the OTA status")
                    if restart_otaclient_count == 10:
                        self.log.info("Try to restart the OTA client to update the OTA status")
                        self.ssh_client.restart_otaclient()
                        restart_otaclient_count = 0
                    else:
                        restart_otaclient_count += 1
                elif current_version == self.ssh_client.get_firmware_version() and current_version == self.test_fw:
                    self.log.info("The firmware version are match, OTA test Passed!")
                    break
                else:
                    raise self.err.TestFailure('Firmware version are not match, OTA test Failed!')

            time.sleep(self.ota_retry_delay)

        if not self.test_fw:
            # The OTA never started and the status didn't change
            raise self.err.TestFailure('OTA did not execute successfully, check if the downgrade version: '
                                       '{} is higher than the OTA bucket, or there is any issue on the cloud server'
                                       .format(self.start_fw))

    def check_db_migration(self):
        db_migration_info_list = self.ssh_client.get_db_migration_info()
        if db_migration_info_list:
            # There might be multiple db migration info, calculate
            for db_info in db_migration_info_list:
                self.log.warning("db_info: {}".format(db_info))
                db_from = db_info.get('from')
                db_to = db_info.get('to')
                db_elapsed_time = db_info.get('elapsedTime')
                """ 
                Not all the migrated information has rebuildFTS flag, 
                if any of the rebuildFTS flag is found and is True, 
                check the FTS migration time in the next steps
                """
                if db_info.get('rebuildFTS'):
                    self.rebuild_fts = db_info.get('rebuildFTS')
                if db_from == '0' and db_to == '1':
                    continue
                else:
                    self.log.warning("DB migration from: {0} to: {1}, elapsed time: {2} ms".format(
                        db_from, db_to, round(float(db_elapsed_time)/1000, 2)))
                    self.db_time_total += int(db_elapsed_time)
                    if not self.db_from_overall or int(self.db_from_overall) > int(db_from):
                        self.db_from_overall = db_from
                    if not self.db_to_overall or int(self.db_to_overall) < int(db_to):
                        self.db_to_overall = db_to
            self.db_time_total = round(float(self.db_time_total)/1000, 2)
            self.log.info('DB migration total elapsedTime: {} ms'.format(self.db_time_total))
            self.log.info("Rebuild FTS: {}".format(self.rebuild_fts))
            self.rebuild_fts_time = None
            if self.rebuild_fts:
                retry = 0
                retry_delay = 60
                max_retries = 10
                while True:
                    result = self.ssh_client.get_fts_rebuild_info()
                    if not result:
                        if retry < max_retries:
                            self.log.info("Cannot find FTS rebuild info, retry after {0} seconds, {1} retries left...".
                                          format(retry_delay, (max_retries - retry)))
                            time.sleep(retry_delay)
                            retry += 1
                        else:
                            raise self.err.StopTest(
                                'Cannot find FTS rebuild info after {} retries!'.format(max_retries))
                    else:
                        self.log.info("Rebuild FTS info: {}".format(result))
                        self.rebuild_fts_time = str(result.get('elapsedTime'))
                        if self.rebuild_fts_time and 'ms' in self.rebuild_fts_time:
                            self.rebuild_fts_time = self.rebuild_fts_time.split('ms')[0]
                        self.log.warning("FTS rebuild time: {}".format(self.rebuild_fts_time))
                        break

        with open("output/db_migration.txt", "w") as f:
            # time is in ms format
            f.write("FW_TO_VERSION={}\n".format(self.test_fw))
            f.write("RESTSDK_INDEXING_TIME={}\n".format(self.restsdk_indexing_elapsed_time))
            f.write("DB_MIGRATION_TIME={}\n".format(self.db_time_total))
            f.write("DB_MIGRATION_FROM={}\n".format(self.db_from_overall))
            f.write("DB_MIGRATION_TO={}\n".format(self.db_to_overall))
            if self.rebuild_fts:
                f.write("FTS_REBUILD_TIME={}\n".format(self.rebuild_fts_time))

    def compare_dataset_checksum(self):
        if not self.special_dataset:
            folder_md5_after = self.ssh_client.get_folder_md5_checksum("/shares/{}".format(self.share_folder_name))
            self.log.warning("Test data folder MD5 (after): {}".format(folder_md5_after))

            if self.folder_md5_before == folder_md5_after:
                self.log.info("Data integrity check PASSED!")
                # Clean the share folder info here because we want to keep the folder when md5 comparison failed
                self.log.info("Deleting the restsdk filesystem of test share folder")
                self.uut_owner.delete_filesystem(self.filesystem_id)
                self.log.info("Deleting test share folder")
                self.ssh_client.delete_share(self.share_folder_name)
            else:
                raise self.err.TestFailure("Data integrity check FAILED!")

    def calculate_indexing_elapsed_time(self, start_time, end_time):
        start_time = self.parse_the_datetime_in_iso_format(start_time)
        end_time = self.parse_the_datetime_in_iso_format(end_time)
        diff = (end_time - start_time).total_seconds() * 1000
        return diff

    def check_timeout(self, start_time, timeout):
        time_elapsed = time.time() - start_time
        if time_elapsed > timeout:
            self.log.warning("Reached timeout: {}".format(timeout))
            return True
        else:
            self.log.info("{} seconds left before the OTA timeout".format(int(timeout-time_elapsed)))

    @staticmethod
    def parse_the_datetime_in_iso_format(date):
        # 2021-03-09T23:16:38.018051525-08:00 -> 2021-03-09 23:16:38.018051
        date = date.rsplit('-', 1)[0]
        date = date[:len(date) - 3]
        date = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%f')
        return date


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Get_Device_info test on Kamino Android ***
        Examples: ./run.sh godzilla_scripts/functional_tests/ota_disable_auto_update.py \
        --uut_ip 10.136.137.159 -env dev1 
        """)
    parser.add_argument('-sf', '--start_fw', help='Start firmware version, ex. 5.19.117')
    parser.add_argument('--file_server_ip', help='File server IP address', default='10.200.141.26')
    parser.add_argument('--local_image', action='store_true', default=False,
                        help='Download ota firmware image from local file server')
    parser.add_argument('--ota_timeout', help='The maximum ota timeout value', type=int, default=3600)
    parser.add_argument('--ota_retry_delay', help='How many seconds between each ota request', type=int, default=10)
    parser.add_argument('--keep_fw_img', action='store_true', default=False, help='Keep downloaded firmware')
    parser.add_argument('-oid', '--ota_bucket_id', help='Specified bucket id, can input "default" or "special" '
                                                        'to load the bucket id from constant file.', default="default")
    parser.add_argument('-um', '--update_mode', help='The mode to execute OTA update',
                        default="now", choices=["now", "random", "daily", "weekly", "n_plus_one"])
    parser.add_argument('--dir_in_file_server', help='The db_migration dataset path in file server',
                        default='/test/IOStress/')
    parser.add_argument('-sd', '--special_dataset', help='The share folder name of existed dataset for db migration', default=None)
    parser.add_argument('--skip_data_integrity', action='store_true', help='Skip upload files and compare checksum')

    test = OTAUpdateNow(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
