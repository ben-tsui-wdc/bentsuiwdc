# -*- coding: utf-8 -*-

__author__ = "Vance Lo <vance.lo@wdc.com>"
__author2__ = "Ben Tsui <ben.tsui@wdc.com"


# std modules
import os
import sys
import time
import shutil
from pprint import pformat
from requests import ConnectionError

# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from middleware.error import TestSkipped
from platform_libraries.cloud_api import CloudAPI
from platform_libraries.restAPI import RestAPI
from kdp_scripts.bat_scripts.firmware_update import FirmwareUpdate
from kdp_scripts.bat_scripts.factory_reset import FactoryReset
from jenkins_scripts.update_bucket import OTABucket
from platform_libraries.constants import KDP
from platform_libraries.constants import RnD
from platform_libraries.common_utils import ClientUtils
from kdp_scripts.bat_scripts.check_nasadmin_daemon import CheckNasAdminDaemon


class OTA_Daily_Stress(KDPTestCase):

    TEST_SUITE = 'OTA_Test'
    TEST_NAME = 'OTA_Test'
    TEST_JIRA_ID = 'KDP-1241,KDP-1233,KDP-5510,KDP-1251,KDP-3311,KDP-905'
    REPORT_NAME = 'OTA'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.test_fw = None
        self.start_fw = "8.2.0-217"
        self.file_server_ip = "fileserver.hgst.com"
        self.dir_in_file_server = "/test/IOStress/"
        self.local_image = False
        self.S3_image = False
        self.ota_timeout = 60 * 60
        self.ota_retry_delay = 15
        self.keep_fw_img = True
        self.ota_bucket_id = None
        self.loop_interval = 10
        self.update_mode = 'normal'
        self.app_id = None
        self.skip_data_integrity = False
        self.skip_factory_reset = False
        self.led_test = False
        self.local_image_path = None

    def init(self):
        self.cloud_api = CloudAPI(env=self.env.cloud_env)
        restsdk_url_prefix = 'http://{}'.format(self.env.uut_ip)
        if self.env.uut_restsdk_port:
            restsdk_url_prefix += ':{}'.format(self.env.uut_restsdk_port)
        self.uut_owner = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env, username=self.env.username,
                                 password=self.env.password, init_session=False,
                                 url_prefix=restsdk_url_prefix, stream_log_level=self.env.stream_log_level)
        self.client_utils = ClientUtils()
        self.model_name = self.ssh_client.get_model_name()
        self.rnd_device = self.ssh_client.check_is_rnd_device()
        if self.rnd_device:
            self.user_roots_path = RnD.USER_ROOT_PATH
        else:
            self.user_roots_path = KDP.USER_ROOT_PATH

        if self.ota_bucket_id == 'special':
            self.bucket_id = KDP.SPECIAL_BUCKET_ID_V2.get(self.model_name).get(self.env.cloud_env)
            self.log.info("Test with special OTA bucket id: {}".format(self.bucket_id))
        elif self.ota_bucket_id == 'default' or not self.ota_bucket_id:
            self.bucket_id = KDP.DEFAULT_BUCKET_ID_V2.get(self.model_name).get(self.env.cloud_env)
            self.log.info("Test with default OTA bucket id: {}".format(self.bucket_id))
        else:
            self.bucket_id = self.ota_bucket_id
        if not self.bucket_id:
            raise self.err.TestSkipped('Cannot find bucket id for model: {}, env: {} in the constant file!'.
                                       format(self.model_name, self.env.cloud_env))

        if self.update_mode == "n_plus_one":
            self.TEST_JIRA_ID = 'KDP-1239,KDP-5510,KDP-1251'
            self.downgrade_fw_version = self.env.firmware_version
        else:
            self.downgrade_fw_version = self.start_fw

        if self.downgrade_fw_version.endswith('.s'):
            self.is_gpkg = True
        else:
            self.is_gpkg = False

        self.fw_image_folder = '{}/firmware_update'.format(KDP.DATA_VOLUME_PATH.get(self.model_name))
        self.ota_log_path = '/var/log/otaclient.log'

        # Data info for checking integrity
        self.LOCAL_UPLOAD_FOLDER = os.path.join(os.getcwd(), 'upload_data_before_ota')
        self.FILE_LIST = list()
        self.test_folder_md5sum_before = None
        self.test_folder_md5sum_after = None
        self.SINGLE_TEST_FILE = 'dummyfile'
        self.SINGLE_TEST_FILE_MD5 = None

    def before_loop(self):
        self.log.info("Before Loop Step 1: Clean up the firmware image folder before testing")
        # This is to prevent the firmware signing verification failed when we switch different fw version
        if self.ssh_client.check_file_in_device(self.fw_image_folder):
            self.ssh_client.execute_cmd('rm -r {}'.format(self.fw_image_folder))

    def before_test(self):
        # Replace sshd for 9.4/9.5 firmware
        self.usb_path = self.ssh_client.get_usb_path()
        self.sshd_940_folder = '{}/sshd_940'.format(self.usb_path)
        self.sshd_950_folder = '{}/sshd_950'.format(self.usb_path)
        self.switch_sshd = False

        self.log.info('Before Test Step 1: Check if the test firmware version matches the bucket to_version')
        self.check_to_version_in_ota_bucket()

        self.log.info("Before Test Step 2: Check if we need to download sshd from file server")
        if self.start_fw.startswith('9.4') and self.test_fw.startswith('9.5'):
            self.switch_sshd = True
            self.log.info('Need to switch sshd during testing, start downloading the files')
            self.ssh_client.remount_usb(self.usb_path)
            file_server_940_path = '{}/KDP/ssh_cert/9.4.0-191_debian10'.format(self.file_server_ip)
            self.download_sshd(file_server_940_path, self.sshd_940_folder)
            file_server_950_path = '{}/KDP/ssh_cert/9.5.0-101_debian11'.format(self.file_server_ip)
            self.download_sshd(file_server_950_path, self.sshd_950_folder)
            self.ssh_client.execute('cp {}/sshd* {}'.format(self.sshd_940_folder, self.usb_path))

        self.log.info("Before Test Step 3: Downgrade the firmware to {}, run factory reset and attach owner".
                      format(self.downgrade_fw_version))
        self.downgrade_firmware()
        if not self.skip_factory_reset:
            self.factory_reset_after_downgrade()
        else:
            self.log.info("skip_factory_reset flag is true, skip this test step!")
        self.uut_owner.init_session()
        self.log.info("Wait for 30 seconds after attaching the owner")
        time.sleep(30)

        self.log.info("Before Test Step 4: Prepare test files and upload to the device for data integrity test")
        if self.skip_data_integrity:
            self.log.info("skip_data_integrity flag is true, skip this test step!")
        else:
            self.download_test_data_from_file_server()
            self.upload_test_data_to_device()
            self.create_single_test_file_and_get_local_checksumm()
            # Todo: porting the step 3 (restsdk indexing) in GZA ota_update_now

        self.log.info("Before Test Step 5: Install an APP to test app migration")
        self.install_app()

    def test(self):
        self.log.info("Test Step 1: Add device id in the OTA bucket")
        self.add_device_id_in_the_ota_bucket()

        self.log.info("Test Step 2: If it's N+1 test, modify the fw version to the older one")
        self.modify_fw_version_for_n_plus_one()

        self.log.info("Test Step 3: Start to wait for the device OTA to the new version: {}".format(self.test_fw))
        self.trigger_ota()

        self.log.info("Test Step 4: Verify the current firmware version after OTA completed")
        self.check_ota_update_status()
        if not self.skip_data_integrity:
            self.check_data_integrity_after_ota()
            self.upload_single_file_after_ota()

    def check_data_integrity_after_ota(self):
        self.test_folder_md5sum_after = self.get_data_checksum()
        self.log.warning("MD5 before: {}".format(self.test_folder_md5sum_before))
        self.log.warning("MD5 after: {}".format(self.test_folder_md5sum_after))
        if self.test_folder_md5sum_before == self.test_folder_md5sum_after:
            self.log.info("Data integrity check PASSED!")
            # Todo: Need to add restsdk indexing first
            # Clean the share folder info here because we want to keep the folder when md5 comparison failed
            # self.log.info("Deleting the restsdk filesystem of test share folder")
            # self.uut_owner.delete_filesystem(self.filesystem_id)
        else:
            raise self.err.TestFailure("Data integrity check FAILED!")

        # Todo: Porting the Step 7 & 8 in ota_stress.py to here (dummyfile ul/dl after each iteration)

    def upload_single_file_after_ota(self):
        with open(os.path.join(self.LOCAL_UPLOAD_FOLDER, self.SINGLE_TEST_FILE), 'rb') as f:
            self.uut_owner.chuck_upload_file(file_object=f, file_name=self.SINGLE_TEST_FILE)

        user_id = self.uut_owner.get_user_id(escape=True)
        data_path = "{0}/{1}/{2}".format(self.user_roots_path, user_id, self.SINGLE_TEST_FILE)
        single_file_checksum = self.ssh_client.get_file_md5_checksum(data_path)
        if single_file_checksum == self.SINGLE_TEST_FILE_MD5:
            self.log.info("Upload single file and compare checksum PASSED after OTA")
        else:
            raise self.err.TestFailure("Upload single file and compare checksum FAILED after OTA!")

    def after_test(self):
        self.log.info("After Test Step 1: Force upload the logs")
        self.ssh_client.log_rotate_kdp(force=True)
        self.ssh_client.log_upload_kdp(reason="Test")

        self.log.info("After Test Step 2: Check if the device auto ota need to be locked")
        if not self.env.enable_auto_ota:
            self.log.info('enable_auto_ota is set to false, lock otaclient service')
            self.ssh_client.lock_otaclient_service_kdp()

        self.log.info("After Test Step 3: Sleep {} seconds between each iteration".format(self.loop_interval))
        if int(self.loop_interval) > 0:
            time.sleep(int(self.loop_interval))

    def after_loop(self):
        self.log.info("After Loop Step 1: Remove local data set")
        if os.path.exists(self.LOCAL_UPLOAD_FOLDER):
            shutil.rmtree(self.LOCAL_UPLOAD_FOLDER)

        if os.path.exists(self.SINGLE_TEST_FILE):
            os.remove(self.SINGLE_TEST_FILE)

    """ Before Test Steps """
    def check_to_version_in_ota_bucket(self):
        bucket_last_promoted_info = self.cloud_api.get_ota_bucket_last_promoted_build(self.bucket_id)
        # OTA_BUCKET = OTABucket(env=self.env.cloud_env, ver=self.test_fw, bid=self.bucket_id,
        #                        model=self.model_name, gpkg=self.is_gpkg)
        # bucket_info = OTA_BUCKET.get_ota_specific_buckets_info()
        # self.log.info('OTA bucket info: \n{}'.format(pformat(bucket_info)))
        if not self.test_fw or self.test_fw.lower() in ("auto", "none"):
            self.log.warning("Test version is not specified, will use the bucket version:{} to test".
                             format(bucket_last_promoted_info))
            self.test_fw = bucket_last_promoted_info
        else:
            # Todo: Do we really want to update buckets here?
            if self.test_fw != bucket_last_promoted_info:
                raise self.err.TestSkipped("Test version does not match the to_version in default bucket")
            # if self.test_fw != bucket_to_version:
            #     self.log.warning("test_fw={}".format(self.test_fw))
            #     if self.ota_bucket_id:
            #         self.log.warning("Test version does not match the to_verion in special bucket, "
            #                          "will update the bucket")
            #         OTA_BUCKET.update_bucket(update_bucket_name=None, update_start_version=None)
            #         bucket_to_version = OTA_BUCKET.get_ota_specific_buckets_info()['to_version']
            #         self.log.warning("Double checked bucket new to_version is: {}".format(bucket_to_version))
            #         if self.test_fw != bucket_to_version:
            #             raise self.err.TestSkipped("Failed to update bucket to specified version! Stop the test!")
            #     else:
            #         raise self.err.TestSkipped("Test version does not match the to_version in default bucket")

    def download_test_data_from_file_server(self):
        if not os.path.exists(self.LOCAL_UPLOAD_FOLDER):
            os.mkdir(self.LOCAL_UPLOAD_FOLDER)

        self.log.info("Download test files({0}) from file server({1}) to upload folder".
                      format(self.dir_in_file_server, self.file_server_ip))
        download_path = '{0}{1}'.format('ftp://ftp:ftppw@{}'.format(self.file_server_ip), self.dir_in_file_server)
        cur_dir = self.dir_in_file_server.count('/')
        cmd = 'wget -N --no-host-directories --cut-dirs={0} -r {1} -P {2}'.\
            format(cur_dir, download_path, self.LOCAL_UPLOAD_FOLDER)
        os.popen(cmd)

        if not self.FILE_LIST:
            for (dirpath, dirnames, filenames) in os.walk(self.LOCAL_UPLOAD_FOLDER):
                self.FILE_LIST.extend(filenames)
                break

    def get_data_checksum(self):
        user_id = self.uut_owner.get_user_id(escape=True)
        data_path = "{0}/{1}".format(self.user_roots_path, user_id)
        folder_checksum = self.ssh_client.get_folder_md5_checksum(data_path)
        if folder_checksum:
            return folder_checksum
        else:
            raise self.err.TestSkipped("Failed to get MD5 checksum of folder: {}".format(data_path))

    def upload_test_data_to_device(self):
        self.log.info('Start to upload test files to the device')
        for index, file_name in enumerate(self.FILE_LIST):
            with open(os.path.join(self.LOCAL_UPLOAD_FOLDER, file_name), 'rb') as f:
                self.log.debug("Uploading file: {0} into test device".format(file_name))
                self.uut_owner.chuck_upload_file(file_object=f, file_name=file_name)

        self.log.info("Get the dataset checksum before OTA")
        self.test_folder_md5sum_before = self.get_data_checksum()

    def create_single_test_file_and_get_local_checksumm(self):
        if not os.path.exists(self.SINGLE_TEST_FILE):
            self.log.info("Create a dummyfile for upload/download test after each iteration")
            self.client_utils.create_random_file(file_name=self.SINGLE_TEST_FILE)

        if not self.SINGLE_TEST_FILE_MD5:
            self.SINGLE_TEST_FILE_MD5 = self.client_utils.md5_checksum(self.SINGLE_TEST_FILE)
            if not self.SINGLE_TEST_FILE_MD5:
                raise self.err.TestSkipped('Failed to get the local dummy md5 checksum!')

    def downgrade_firmware(self):
        if self.is_gpkg:
            fw_ver_to_fwupdate = self.downgrade_fw_version.replace('.s', '')
        else:
            fw_ver_to_fwupdate = self.downgrade_fw_version

        env_dict = self.env.dump_to_dict()
        env_dict['firmware_version'] = fw_ver_to_fwupdate
        env_dict['local_image'] = self.local_image
        env_dict['S3_image'] = self.S3_image
        env_dict['keep_fw_img'] = self.keep_fw_img
        env_dict['force_update'] = False
        env_dict['clean_restsdk_db'] = False
        env_dict['enable_auto_ota'] = False
        env_dict['uut_owner'] = False
        env_dict['include_gpkg'] = self.is_gpkg
        env_dict['local_image_path'] = self.local_image_path
        firmware_update = FirmwareUpdate(env_dict)
        try:
            firmware_update.main()
            downgraded_fw = self.ssh_client.get_firmware_version()
            if downgraded_fw != self.downgrade_fw_version:
                raise self.err.TestSkipped("Downgrade firmware was failed! Skipped the test!")
        except TestSkipped:
            self.log.info("No need to downgrade the firmware, continue testing")

        self.log.info("Stop the otaclient to avoid OTA starts before the OTA lock is disabled")
        self.ssh_client.stop_otaclient_service()

    def factory_reset_after_downgrade(self):
        env_dict = self.env.dump_to_dict()
        env_dict['enable_auto_ota'] = False
        factory_reset = FactoryReset(env_dict)
        factory_reset.stop_ota_client = False
        factory_reset.main()

        self.log.info("Stop the otaclient to avoid OTA starts before the OTA lock is disabled")
        self.ssh_client.stop_otaclient_service()

    def modify_fw_version_for_n_plus_one(self):
        if self.update_mode == "n_plus_one":
            self.ssh_client.execute('echo "{}" > /etc/version'.format(self.start_fw))
            self.log.info("Start the otaclient to let the cloud OTA update latest status")
            self.ssh_client.start_otaclient_service()
            time.sleep(5)
            self.log.info("Stop the otaclient again to avoid OTA starts before the OTA lock is disabled")
            self.ssh_client.stop_otaclient_service()

    def install_app(self):
        if self.app_id:
            self.uut_owner.install_app_kdp(self.app_id)
            if not self.uut_owner.wait_for_app_install_completed(self.app_id):
                raise self.err.TestFailure('Failed to install APP({})!'.format(self.app_id))
            self.log.info("APP ({}) has been installed".format(self.app_id))
        else:
            self.log.info("Skip APP install since the app_id is not specified")

    def download_sshd(self, file_server_path, device_path):
        if self.ssh_client.check_folder_in_device(device_path):
            self.log.info("The sshd folder: {} already exist, skip download steps".format(device_path))
        else:
            self.ssh_client.create_folder(device_path)
            self.ssh_client.download_file('{}/sshd'.format(file_server_path), dst_path=device_path)
            self.ssh_client.download_file('{}/{}/sshd.cert'.format(file_server_path, self.model_name),
                                          dst_path=device_path)

    """ Test Steps """
    def add_device_id_in_the_ota_bucket(self):
        self.device_id = self.ssh_client.get_device_id()
        cloud_ota_info, local_ota_status = self.get_ota_status_with_retries()
        self.log.info('Original OTA status: \n{}'.format(pformat(cloud_ota_info)))

        if self.bucket_id != cloud_ota_info.get('bucketId'):
            self.log.info("Bucket id not match, add device to the specified bucket id: {}".format(self.bucket_id))
            self.cloud_api.add_device_in_ota_bucket(self.bucket_id, [self.device_id])
        else:
            self.log.info('Device is already in the bucket id: {}, no need to add device to bucket'.format(self.bucket_id))

        self.log.info("Start the otaclient to let the cloud OTA update latest status")
        self.ssh_client.start_otaclient_service()
        time.sleep(5)
        self.log.info("Stop the otaclient again to avoid OTA starts before the OTA lock is disabled")
        self.ssh_client.stop_otaclient_service()

        cloud_ota_info, local_ota_status = self.get_ota_status_with_retries()
        self.log.info('Updated OTA status: \n{}'.format(pformat(cloud_ota_info)))

    def get_ota_status_with_retries(self):
        cloud_retries_delay = 60
        cloud_retries_max = int(self.ota_timeout/cloud_retries_delay)
        cloud_retries = 0
        while cloud_retries < cloud_retries_max:
            try:
                cloud_ota_info = self.cloud_api.get_ota_status(self.device_id).get('data')
            except ConnectionError as e:
                self.log.warning("Failed to connect to the server, retry after {} secs. Error message: {}".
                                 format(cloud_retries_delay, repr(e)))
                cloud_retries += 1
                time.sleep(cloud_retries_delay)
                continue
            if not cloud_ota_info:
                if cloud_retries == cloud_retries_max:
                    raise self.err.TestFailure("Cannot get the OTA information in {} minutes!".format(cloud_retries_max))
                self.log.warning("Cannot get the OTA information from the cloud! Wait for {} secs to retry, "
                                 "{} retries left...".format(cloud_retries_delay, cloud_retries_max - cloud_retries))
                cloud_retries += 1
                self.ssh_client.restart_otaclient()
                time.sleep(cloud_retries_delay)
            else:
                local_ota_status = self.ssh_client.get_local_ota_status()
                if local_ota_status == "downloading":
                    dl_process, dl_rate = self.ssh_client.get_local_ota_download_progress()
                    if dl_process and dl_rate:
                        local_ota_status += ", percent: {0}%, rate: {1} KB/s".\
                            format(round(float(dl_process), 2), round(float(dl_rate), 2))

                self.log.info("===== OTA Status =====")
                self.log.info("cloud currVersion: {}".format(cloud_ota_info.get('currVersion')))
                self.log.info("cloud sentVersion: {}".format(cloud_ota_info.get('sentVersion')))
                self.log.info("cloud ota status: {}".format(cloud_ota_info.get('status')))
                self.log.info("local ota status: {}".format(local_ota_status))
                return cloud_ota_info, local_ota_status

    def trigger_ota(self):
        ota_started = False
        ota_status = None
        wait_sent_to_device_count = 0
        self.ota_start_time = time.time()
        self.log.info("OTA timeout = {} seconds".format(self.ota_timeout))
        self.log.info("OTA retry delay = {} seconds".format(self.ota_retry_delay))

        if self.switch_sshd:
            # Check the usb path again since it might be changed during previous test steps
            self.usb_path = self.ssh_client.get_usb_path()
            self.sshd_950_folder = '{}/sshd_950'.format(self.usb_path)
            self.ssh_client.remount_usb(self.usb_path)
            self.ssh_client.execute('cp {}/sshd* {}'.format(self.sshd_950_folder, self.usb_path))

        ### LED_TEST_PART1_begin (KDP-905)
        if self.led_test:
            pwm_duty_rate_path = KDP.PWM_DUTY_RATE_PATH.get(self.uut['model'])
            # To acquire current led brightness, if it is about 50%, need to turn it into 100% (where HDD is active).
            stdout, stderr = self.ssh_client.execute_cmd('cat {}'.format(pwm_duty_rate_path))
            if float(stdout.split('%')[0])/100 < 0.6:  # That means HDD is in standby mode. Need to make HDD active.
                device_vol_path = self.ssh_client.getprop(name='device.feature.vol.path')
                # Make HDD active
                self.ssh_client.execute_cmd('touch {}/test'.format(device_vol_path))
                self.ssh_client.execute_cmd('rm {}/test'.format(device_vol_path))
                start_time = time.time()
                while True:
                    stdout, stderr = self.ssh_client.execute_cmd('cat {}'.format(pwm_duty_rate_path))
                    if float(stdout.split('%')[0])/100 > 0.9:  # Confirm the led brightness is > 90%, that means HDD active.
                        break
                    elif time.time() - start_time > 300:
                        for drive in self.ssh_client.get_sys_slot_drive():
                            result = self.ssh_client.get_drive_state(drive)
                        raise self.err.TestError('The led pwm_duty_rate is still {}. Please check HDD status above.'.format(stdout))
                    time.sleep(3)
            initial_led_list = self.ssh_client.get_led_logs(cmd='grep -r led_ctrl_server /var/log/analyticpublic.log')
            led_check = True
        ### LED_TEST_PART1_end (KDP-905)

        while True:
            if self.check_timeout(self.ota_start_time, self.ota_timeout):
                raise self.err.TestFailure('OTA reaches the timeout and still not update succussfully! '
                                           'The last update status: {}'.format(ota_status))
            cloud_ota_info, local_ota_status = self.get_ota_status_with_retries()
            current_version = cloud_ota_info.get('currVersion')
            sent_version = cloud_ota_info.get('sentVersion')
            ota_status = cloud_ota_info.get('status')

            ### LED_TEST_PART_2 (KDP-905)
            if self.led_test:
                if ota_status == 'updateReboot':
                    led_check = False
                if led_check:
                    # Keep checking led status until device is going to be rebooted.
                    led_list = self.ssh_client.get_led_logs(cmd='grep -r -i led_ctrl_server /var/log/analyticpublic.log')
                    if led_list == initial_led_list or led_list == None:  # Becasue sometimes the /var/log will be rotated or uploaded.
                        pass
                    else:
                        raise self.err.TestFailure('There are unknown led log occurred.')
                    stdout, stderr = self.ssh_client.execute_cmd('cat {}'.format(pwm_duty_rate_path))
                    if float(stdout.split('%')[0])/100 < 0.9:
                        raise self.err.TestFailure('The led brightness should be 99% or 100%.')
            ### LED_TEST_PART_2 (KDP-905)

            if ota_status == "updateFail" and not ota_started:
                self.log.info("OTA status is updateFail before testing due to OTA lock, try to modify the status")
                self.cloud_api.update_device_ota_status(self.device_id, status="updateReboot")
                self.log.info("Restart otaclient to let the new status work")
                self.ssh_client.restart_otaclient()
                continue

            if (current_version != self.start_fw or sent_version != self.test_fw) and not ota_started:
                if current_version != self.start_fw:
                    self.log.info("Device OTA cloud currVersion: {0} doesn't sync local firmware version: {1}".
                                  format(current_version, self.start_fw))
                if sent_version != self.test_fw:
                    self.log.info("Device OTA cloud sentVersion: {0} doesn't sync OTA bucket toVersion: {1}".
                                  format(sent_version, self.test_fw))
                self.log.info("Try to restart otaclient to update cloud info")
                self.ssh_client.restart_otaclient()
            else:
                if not ota_started:
                    self.log.info('OTA start running, disable the OTA lock')
                    self.ssh_client.unlock_otaclient_service_kdp()
                    self.ssh_client.restart_otaclient()
                    ota_started = True
                else:
                    if ota_status == "updateOk":
                        self.log.info("OTA completed, checking firmware version and device status")
                        if current_version != sent_version:
                            self.log.warning("Expect firmware version: {0}, current cloud firmware version: {1}".
                                             format(sent_version, current_version))
                            self.log.warning("OTA current_version doesn't match sent_version, retry after {} seconds".
                                             format(self.ota_retry_delay))
                            time.sleep(self.ota_retry_delay)
                        else:
                            self.ssh_client.wait_for_device_boot_completed()
                            if self.env.is_nasadmin_supported():
                                env_dict = self.env.dump_to_dict()
                                check_nasadmin_daemon = CheckNasAdminDaemon(env_dict)
                                check_nasadmin_daemon.main()
                            break
                    elif ota_status == "updateReboot" and local_ota_status == "updateOk":
                        self.log.warning("OTA should complete, the cloud status was not updated due to network issue")
                        break
                    else:
                        OTA_FAILED = ['downloadFail', 'unzipFail', 'updateFail', 'bootloaderUpdateFail', 'updateFailAfterReboot']
                        if ota_status in OTA_FAILED:
                            raise self.err.TestFailure("OTA status is in '{}', Test Failed!".format(ota_status))

                        if ota_status == "SENT_TO_DEVICE":
                            if wait_sent_to_device_count == 60:
                                self.log.warning('The cloud ota status is stuck at "SENT_TO_DEVICE" for {} seconds'.
                                                 format(wait_sent_to_device_count * self.ota_retry_delay))
                                self.log.warning("The download process might timeout due to network issue, "
                                                 "try to restart the OTA client")
                                self.ssh_client.restart_otaclient()
                                wait_sent_to_device_count = 0
                            else:
                                wait_sent_to_device_count += 1

            time.sleep(self.ota_retry_delay)

    def check_ota_update_status(self):
        current_version_local = self.ssh_client.get_firmware_version()
        if current_version_local != self.test_fw:
            raise self.err.TestFailure("Expect firmware version: {0}, current firmware version: {1}".
                                       format(self.test_fw, current_version_local))
        else:
            self.log.info("OTA test PASSED!")

    """ Utilities """
    def check_timeout(self, start_time, timeout):
        time_elapsed = time.time() - start_time
        if time_elapsed > timeout:
            self.log.warning("Reached timeout: {}".format(timeout))
            return True
        else:
            self.log.info("{} seconds left before the OTA timeout".format(int(timeout-time_elapsed)))
            return False


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** OTA stress test script on KDP ***
        Examples: ./start.sh kdp_scripts/stress_tests/ota_daily_stress.py --uut_ip 10.200.141.12 \
                  -env qa1 -lt 3 --local_image --start_fw 8.0.0-217 --test_fw 8.0.0-220
        """)
    # Test Arguments
    parser.add_argument('--test_fw', help='Update test firmware version, ex. 8.0.0-217', default=None)
    parser.add_argument('--start_fw', help='Start firmware version, ex. 4.0.1-611', default='8.0.0-217')
    parser.add_argument('--file_server_ip', help='File server IP address', default='fileserver.hgst.com')
    parser.add_argument('--dir_in_file_server', help='The data set dir in file server', default='/test/IOStress/')
    parser.add_argument('--local_image', action='store_true', default=False,
                        help='Download ota firmware image from local file server')
    parser.add_argument('--S3_image', action='store_true', default=False,
                        help='Download ota firmware image from S3 bucket server')
    parser.add_argument('--ota_timeout', help='The maximum ota timeout value', type=int, default=60*60)
    parser.add_argument('--ota_retry_delay', help='The delay time between retries when getting cloud ota status', type=int, default=15)
    parser.add_argument('--keep_fw_img', action='store_true', default=True, help='Keep downloaded firmware')
    parser.add_argument('--ota_bucket_id', help='Choose "default", "special" buckets or specify the bucket id', default='default')
    parser.add_argument('--loop_interval', help='sleep time between each iteration', default=10)
    parser.add_argument('--update_mode', help='The mode to execute OTA update', default="normal",
                        choices=["normal", "n_plus_one"])
    parser.add_argument('-appid', '--app_id', help='App ID to installed', default=None)
    parser.add_argument('--skip_data_integrity', action='store_true', help='Skip upload files and compare checksum')
    parser.add_argument('--skip_factory_reset', action='store_true',
                        help='Skip factory reset after fw downgrade if we know the RestSDK DB version is the same')
    parser.add_argument('--led_test', action='store_true',
                        help='led test while OTA is in progress.')
    parser.add_argument('--local_image_path', default=None, help='Specify the absolute path of local firmware image')
    test = OTA_Daily_Stress(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)