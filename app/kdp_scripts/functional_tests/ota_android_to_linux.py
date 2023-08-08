# -*- coding: utf-8 -*-
""" Test cases to run OTA from KAM(android) to KDP(linux) firmware.
"""
__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import os
import shutil
import time
import zipfile
import json
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.common_utils import execute_local_cmd
from platform_libraries.adblib import ADB
from platform_libraries.cloud_api import CloudAPI
from platform_libraries.constants import KDP


class Ota_Android_To_Linux(KDPTestCase):
    TEST_SUITE = 'KDP Functional Tests'
    TEST_NAME = 'KDP-3491 - OTA from Android to Linux firmware'
    TEST_JIRA_ID = 'KDP-3491'
    REPORT_NAME = 'Single_run'

    SETTINGS = {
        'uut_owner': True,
        'ssh_client': True
    }

    def declare(self):
        self.file_server_ip = 'fileserver.hgst.com'
        self.app_id = 'com.plexapp.mediaserver.smb'
        self.local_image = False
        self.local_image_path = None
        self.ota_bucket_id = "default"

    def init(self):
        self.timeout = 60 * 20
        self.ota_timeout = 60 * 60
        self.cloud_api = CloudAPI(env=self.env.cloud_env)
        self.adb = ADB(uut_ip=self.env.uut_ip, port=5555)
        self.start_fw = self.env.firmware_version
        self.environment = self.env.cloud_env if self.env.cloud_env else self.uut.get('environment')
        self.fw_update_folder = '/data/wd/diskVolume0/firmware_update'
        self.image = 'install.img'
        self.is_kdp_firmware = False

        # e.g. monarch2 -> monarch, remove it for firmware download and check migration OTA buckets
        self.model = self.uut.get('model').replace('2', '')
        if self.ota_bucket_id == "default" or not self.ota_bucket_id:
            self.migration_bucket_id = KDP.DEFAULT_BUCKET_ID_V2.get(self.model).get(self.env.cloud_env)
        elif self.ota_bucket_id == "special":
            self.migration_bucket_id = KDP.SPECIAL_BUCKET_ID_V2.get(self.model).get(self.env.cloud_env)
        else:
            self.migration_bucket_id = self.ota_bucket_id
        if not self.migration_bucket_id:
            raise self.err.TestSkipped('Cannot find bucket id for model: {}, env: {} in the constant file!'.
                                       format(self.model, self.env.cloud_env))

    def test(self):
        self.log.info("*** Step1: Download the KAM firmware image and scp to device")
        self.download_kam_fw_img_and_scp_to_device()

        self.log.info("*** Step2: Downgrade to KAM firmware")
        self.downgrade_to_kam_firmware()
        self.kam_factory_reset()

        self.log.info("*** Step3: Install Plex app in KAM firmware")
        self.log.info("Skip this step since we don't support app installation in android firmware now")
        """
        if self.model == 'yodaplus':
            self.log.info("ibi device doesn't support Plex app, skip this test step")
        else:
            self.upload_sqlite3()
            self.install_plex_app_kam()
            self.check_app_status()
            self.get_pm_list_and_app_logcat_logs()
            self.app_install_pass_criteria_check()
            self.check_appmgr_db_install()
            self.download_precontent_files_to_plex_folder()
        """

        self.log.info("*** Step4: Add device id in the KDP ota bucket")
        self.add_device_id_in_kdp_ota_bucket()

        self.log.info("*** Step5: Trigger OTA to KDP firmware")
        self.trigger_ota()

        self.log.info("*** Step6: Try to connect SSH protocol and check update status")
        self.check_ota_update_status()
        self.log.warning("Device is upgraded to KDP firmware successfully.")

        """ Skip because we don't support app installation in android firmware now
        self.log.info("*** Step7: Install Plex app again after OTA and check migration status")
        if self.model == 'yodaplus':
            self.log.info("ibi device doesn't support Plex app, skip this test step")
        else:
            self.install_plex_app_kdp()
            self.check_plex_app_migration_status()
            self.check_precontent_files_after_migration()
        """

    def after_test(self):
        if not self.is_kdp_firmware:
            self.log.warning("The device was not OTA to KDP firwmare for some reasons, try to recover it")
            self.connect_adb_with_retries()
            self.add_device_id_in_kdp_ota_bucket()
            self.trigger_ota()
            self.check_ota_update_status()
            self.log.warning("Device was recovered to KDP firmware.")

    def after_loop(self):
        # This is for Jenkins to update test_fw version if it's auto
        with open("output/ota_version.txt", "w") as f:
            f.write("OTA_FW={}\n".format(self.test_fw))

        self.log.info("Update the OTA firmware version to upload to Popcorn server")
        self.FW_BUILD = self.test_fw

        self.log.info("Remove the download folder in the test client after testing")
        if os.path.exists(self.build_name):
            shutil.rmtree(self.build_name, ignore_errors=True)

    """ Test Steps """
    def download_kam_fw_img_and_scp_to_device(self):
        self.log.info("Check if the firmware image already exist in the device")
        self.fw_image_path_on_device = "{0}/{1}_{2}".format(self.fw_update_folder, self.image, self.start_fw)
        if self.ssh_client.check_file_in_device(self.fw_image_path_on_device) and self.firmware_md5_checksum_compare():
            self.log.info("Firmware image already exist in the device and checksum is matched, skip download steps")
        else:
            if self.local_image:
                download_path = 'ftp://ftp:ftppw@{}/firmware'.format(self.file_server_ip)
            else:
                download_path = 'http://repo.wdc.com/content/repositories/projects/MyCloudOS'
                if self.env.cloud_env == 'dev':
                    download_path += '-Dev'

            build_name_by_env = {
                'dev1': '',
                'qa1': '-QA',
                'prod': '-prod',
                'integration': '-integration'
            }
            self.build_name = 'MCAndroid{0}'.format(build_name_by_env.get(self.environment))
            tag = '-{}'.format(self.env.cloud_variant) if self.env.cloud_variant in ('engr', 'user') else ''
            self.fw_img_name = '{0}-{1}-ota-installer-{2}{3}.zip'.format(self.build_name, self.start_fw, self.model, tag)

            if self.local_image:
                download_url = '{0}/{1}'.format(download_path, self.fw_img_name)
            else:
                download_url = '{0}/{1}/{2}/{3}'.format(download_path, self.build_name, self.start_fw, self.fw_img_name)

            self.log.info('***** Start to download firmware image {} *****'.format(self.start_fw))
            if not self.ssh_client.scp:
                self.ssh_client.scp_connect()
            max_retries = 5
            retries = 0
            while retries < max_retries:
                try:
                    if self.local_image_path:
                        self.log.info("Local image path is specified, skip download process")
                        self.safe_unzip(zip_file=self.local_image_path, extractpath=self.build_name)
                    else:
                        self.log.info("Downloading the firmware image to test client and unzip it")
                        if os.path.exists(self.build_name):
                            shutil.rmtree(self.build_name, ignore_errors=True)
                        os.mkdir(self.build_name)
                        execute_local_cmd(cmd='wget -nv -N -t 20 -T 7200 {0} -P {1}'.
                                          format(download_url, self.build_name), timeout=60 * 20)
                        self.safe_unzip(zip_file=os.path.join(self.build_name, self.fw_img_name), extractpath=self.build_name)

                    self.log.info("Uploading the firmware image to test device")
                    if self.ssh_client.check_folder_in_device(self.fw_update_folder):
                        self.ssh_client.execute_cmd('rm -r {}'.format(self.fw_update_folder))
                    self.ssh_client.execute_cmd('mkdir {}'.format(self.fw_update_folder))
                    self.ssh_client.scp_upload("./{0}/{1}".format(self.build_name, self.image),
                                               self.fw_image_path_on_device)
                    self.ssh_client.scp_upload("./{0}/{1}.md5".format(self.build_name, self.image),
                                               self.fw_image_path_on_device + '.md5')
                    if not self.ssh_client.check_file_in_device(self.fw_image_path_on_device):
                        raise self.err.TestFailure("The firmware image does not exist in the device, download failed!")

                    if not self.firmware_md5_checksum_compare():
                        raise

                    valid_fw_image = True
                    break
                except Exception as e:
                    self.log.warning("Download firmware image failed, error message: {}".format(repr(e)))
                    self.log.info("wait for 10 secs to retry, {} retries left...".format(max_retries - retries))
                    retries += 1
                    time.sleep(10)
                finally:
                    if self.ssh_client.scp:
                        self.ssh_client.scp_close()
            if not valid_fw_image:
                raise self.err.TestFailure("Download firmware failed after {} retries!".format(max_retries))

    def reconnect_wifi(self):
        if self.env.ap_ssid:
            ap_ssid = self.env.ap_ssid
            ap_password = self.env.ap_password
        else:
            ap_ssid = 'R7000_24'
            ap_password = 'fituser99'
        self.serial_client.setup_and_connect_WiFi(ssid=ap_ssid, password=ap_password, restart_wifi=True)

    def downgrade_to_kam_firmware(self):
        cbr = self.ssh_client.execute_cmd('cat /proc/device-tree/factory/cbr', quiet=True)[0]
        nbr = self.ssh_client.execute_cmd('cat /proc/device-tree/factory/nbr', quiet=True)[0]
        bna = self.ssh_client.execute_cmd('cat /proc/device-tree/factory/bna', quiet=True)[0]
        bootstate = self.ssh_client.execute_cmd('cat /proc/device-tree/factory/bootstate', quiet=True)[0]
        self.log.info('cbr = {}'.format(cbr))
        self.log.info('nbr = {}'.format(nbr))
        self.log.info('bna = {}'.format(bna))
        self.log.info('bootstate = {}'.format(bootstate))

        self.log.info('***** Start to update firmware image: {} *****'.format(self.start_fw))
        self.ssh_client.unlock_otaclient_service_kdp()
        exitcode, _ = self.ssh_client.execute(command='fw_update {0} -r -v {1}'
                                              .format(self.fw_image_path_on_device, self.start_fw),
                                              timeout=self.timeout)
        if exitcode != 0:
            raise self.err.TestFailure('Executed fw_update command failed!')
        else:
            self.ssh_client.lock_otaclient_service_kdp()
            self.log.info('Execute do_reboot command to reboot device...')
            self.ssh_client.reboot_device()
            self.ssh_client.wait_for_device_to_shutdown()

    def connect_adb_with_retries(self):
        adb_connect_max_retry = 10
        for i in range(1, adb_connect_max_retry):
            try:
                self.log.info('Try to init adb connection, iteration {}'.format(i))
                self.adb.connect()
                break
            except Exception as e:
                self.log.warning(repr(e))
                if i < adb_connect_max_retry:
                    self.log.warning("Retry adb connect after 60 secs")
                    time.sleep(60)
                else:
                    raise self.err.TestFailure("Failed to init adb connection after {} retries".
                                               format(adb_connect_max_retry))
        if not self.adb.wait_for_device_boot_completed(self.timeout):
            raise self.err.TestFailure('Device bootup Failed in {}s !!'.format(self.timeout))
        else:
            self.log.info('Device reboot complete')

    def kam_factory_reset(self):
        self.log.info('Start to run the KAM factory reset')
        if self.model == 'yodaplus':
            self.log.warning('Wait for "FW update" reboot completed.')
            self.serial_client.wait_for_boot_complete(timeout=self.timeout)
            self.serial_client.serial_write("busybox nohup reset_button.sh factory")
            self.serial_client.serial_wait_for_string('init: stopping android....', timeout=self.timeout, raise_error=True)
            self.log.warning('Wait for "reset_button.sh factory" reboot completed.')
            self.serial_client.wait_for_boot_complete(timeout=self.timeout)
            self.reconnect_wifi()
            self.connect_adb_with_retries()
            '''
            self.serial_client.serial_wait_for_string('boot_complete_proc_write: matches', timeout=self.timeout, raise_error=True)
            self.log.warning("Wait for more 90 seconds after booting completed.")
            time.sleep(90)
            # Execute "chown 1000.1010 /data/misc/wifi/wpa_supplicant.conf" then reboot device if wlan0 doesn't work.
            self.serial_client.serial_write("chown 1000.1010 /data/misc/wifi/wpa_supplicant.conf")
            time.sleep(3)
            self.serial_client.serial_write("reboot")
            self.serial_client.serial_wait_for_string('init: stopping android....', timeout=self.timeout, raise_error=True)
            #self.serial_client.serial_wait_for_string('Hardware name: Realtek_RTD1295', timeout=self.timeout, raise_error=False)
            self.log.warning("Wait for 90 seconds for rebooting...")
            time.sleep(90)
            self.serial_client.wait_for_boot_complete(timeout=self.timeout)
            '''
            
            
            '''
            self.serial_client.serial_wait_for_string('Hardware name: Realtek_RTD1295', timeout=self.timeout, raise_error=False)
            '''    
        else:
            self.connect_adb_with_retries()
            self.adb.executeShellCommand('busybox nohup reset_button.sh factory')
            self.log.info('Expect device do rebooting')
            if not self.adb.wait_for_device_to_shutdown():
                raise self.err.TestFailure('Device rebooting Failed !!')
            self.log.info('Device is rebooting...')
            if not self.adb.wait_for_device_boot_completed(self.timeout):
                raise self.err.TestFailure('Device bootup Failed in {}s !!'.format(self.timeout))

        self.log.info("Turn on the OTA lock in the properties")
        self.adb.stop_otaclient()
        self.log.info('Device bootup completed')

    def add_device_id_in_kdp_ota_bucket(self):
        self.device_id = None
        for i in range(0, 60):
            device_info = self.adb.executeShellCommand('curl localhost/sdk/v1/device')[0]
            if 'Failed to connect to localhost' in device_info:
                continue
            self.device_id = json.loads(device_info).get('id')
            if self.device_id:
                break
            else:
                self.log.info('No device_id found. Wait for more 10 seconds and try again. retry #{}'.format(i+1))
                time.sleep(10)
        self.cloud_api.add_device_in_ota_bucket(self.migration_bucket_id, [self.device_id])
        self.log.info("Restart otaclient to let special bucket work")
        self.restart_otaclient()

    def add_device_id_in_kdp_ota_bucket_workaround_for_yodaplus(self):
        self.cloud_api.add_device_in_ota_bucket(self.migration_bucket_id, [self.device_id])
        self.log.info("Restart otaclient to let special bucket work")
        self.restart_otaclient()

    def trigger_ota(self):
        ota_started = False
        ota_retry_delay = 15
        wait_sent_to_device_count = 0
        self.log.info("OTA timeout = {} seconds".format(self.ota_timeout))
        self.log.info("OTA retry delay = {} seconds".format(ota_retry_delay))
        max_retries = int(self.ota_timeout / ota_retry_delay)
        for i in range(0, max_retries):
            self.log.info("Get the latest OTA status")
            result = self.get_ota_status_with_retries()
            self.log.info(json.dumps(result, indent=4, sort_keys=True))
            current_version = result.get('currVersion')
            sent_version = result.get('sentVersion')
            ota_status = result.get('status')
            self.test_fw = sent_version
            self.log.info("** cloud currVersion: {}".format(current_version))
            self.log.info("** cloud sentVersion: {}".format(sent_version))
            self.log.info("** OTA status: {}".format(ota_status))

            if ota_status == "updateFail" and not ota_started:
                self.log.info("OTA status is updateFail before testing due to OTA lock, try to modify the status")
                self.cloud_api.update_device_ota_status(self.device_id, status="updateReboot")
                self.log.info("Restart otaclient to let the new status work")
                self.restart_otaclient()
                continue

            if current_version != self.start_fw and not ota_started:
                self.log.info(
                    "Waiting for the current version updated to start_fw: {} in the cloud".format(self.start_fw))
            elif not sent_version:
                self.log.warning(
                    "The cloud sentVersion is: {}, keep waiting for the clouds to be updated".format(sent_version))
                self.restart_otaclient()
            else:
                if not ota_started:
                    self.log.info("OTA start running, disable the OTA lock'")
                    self.adb.start_otaclient()
                    self.log.info("current_fw: {0}, sent_fw: {1}".
                                  format(current_version, sent_version))
                    ota_started = True
                    time.sleep(5)
                    ota_status = self.get_ota_status_with_retries().get('status')
                if ota_status == "updateOk":
                    self.log.info("OTA completed, checking firmware version and device status")
                    if current_version != sent_version:
                        if i == max_retries:
                            self.log.error("OTA current_version doesn't match sent_version after {} seconds!".
                                           format(self.ota_timeout))
                            raise self.err.TestFailure("Expect firmware version: {0}, current firmware version: {1}".
                                                       format(sent_version, current_version))
                        else:
                            self.log.warning("OTA current_version doesn't match sent_version, retry after {} seconds".
                                             format(ota_retry_delay))
                    else:
                        self.adb.disconnect()
                        break
                else:
                    if ota_status in ['bootloaderUpdateFail', 'updateFailAfterReboot']:
                        raise self.err.TestFailure("OTA status is in '{}', Test Failed!".format(ota_status))
                    elif ota_status in ['downloadFail', 'unzipFail']:
                        self.log.warning('OTA download failed, restart otaclient and try again')
                        self.restart_otaclient()
                    elif ota_status == 'updateFail':
                        self.log.warning('OTA update failed, restart otaclient and try again')
                        lock_file_status = self.adb.executeShellCommand("ls /tmp/ota_lock")[0]
                        self.log.info("Lock file status: {}".format(lock_file_status))
                        if lock_file_status != "":
                            self.log.info("Clean the existed ota_lock file before retry")
                            self.adb.executeShellCommand("rm /tmp/ota_lock")
                        self.restart_otaclient()

                    if i == max_retries:
                        raise self.err.TestFailure(
                            "OTA status is still not 'updateOk' after {} secs!".format(self.ota_timeout))

                    self.log.info("OTA status is: {}, keep waiting...".format(ota_status))
                    if ota_status == "SENT_TO_DEVICE":
                        if wait_sent_to_device_count == 20:
                            self.log.info("Try to restart the OTA client to update the OTA status")
                            self.restart_otaclient()
                            wait_sent_to_device_count = 0
                        else:
                            wait_sent_to_device_count += 1
            self.log.info("Wait for {} seconds...".format(ota_retry_delay))
            time.sleep(ota_retry_delay)

    def check_ota_update_status(self):
        self.ssh_client.connect()
        self.ssh_client.wait_for_device_boot_completed()
        new_firmware_version = self.ssh_client.get_firmware_version()
        if new_firmware_version == self.test_fw:
            self.log.info("Firmware version matched, OTA update passed.")
            self.is_kdp_firmware = True
        else:
            raise self.err.TestFailure("Expect firmware version: {0}, actual firmware version: {1}, OTA update failed!"
                                       .format(self.test_fw, new_firmware_version))

    def get_ota_status_with_retries(self):
        cloud_retries_delay = 60
        cloud_retries_max = int(self.ota_timeout/cloud_retries_delay)
        cloud_retries = 0
        while cloud_retries < cloud_retries_max:
            result = self.cloud_api.get_ota_status(self.device_id).get('data')
            if not result:
                if cloud_retries == cloud_retries_max:
                    raise self.err.TestFailure("Cannot get the OTA information in {} minutes!".format(cloud_retries_max))
                self.log.warning("Cannot get the OTA information from the cloud! Wait for {} secs to retry, "
                                 "{} retries left...".format(cloud_retries_delay, cloud_retries_max - cloud_retries))
                cloud_retries += 1
                time.sleep(cloud_retries_delay)
            else:
                return result

    def upload_sqlite3(self):
        self.log.info('Upload sqlite3 to the device ...')
        self.adb.executeShellCommand("mount -o remount,rw /system")
        self.adb.push(local='app_manager_scripts/sqlite3', remote='/system/bin')

    def install_plex_app_kam(self):
        # In 9.4.0 firmware, restsdk port is changed to 8001, need to revise port after downgrade to Android firmware
        self.uut_owner.update_device_ip(port=80)
        self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']})
        retry_times = 3
        self.timing.start()
        while not self.timing.is_timeout(self.timeout):
            successCode = self.uut_owner.install_app(app_id=self.app_id, retry_times=retry_times)
            if successCode == 204:
                break
            elif successCode == 409:
                self.log.warning('return code {}, send install app request again ...'.format(successCode))
            else:
                self.log.error('Install request response: {}, stop to send request ...'.format(successCode))
                break
            time.sleep(5)

    def check_app_status(self):
        self.log.info('Check app installing status ...')
        self.timing.reset_start_time()
        while not self.timing.is_timeout(self.timeout):
            successCode = self.uut_owner.get_install_app_status(self.app_id)
            if successCode == 200 or successCode == 404:
                self.log.info("Install complete. Error code: {}".format(successCode))
                break
            time.sleep(5)
            self.log.info('Waiting for installation: {}'.format(successCode))
            if self.timing.is_timeout(self.timeout):
                self.log.error('Timeout for waiting app({}) installation'.format(self.app_id))

        self.log.info("Checking the Plex APP status")
        self.log.info(self.uut_owner.get_app_info_kdp(self.app_id))

    def get_pm_list_and_app_logcat_logs(self):
        # Check app installed
        self.pm_list_check = self.adb.executeShellCommand('pm list package | grep {}'.format(self.app_id))
        if self.pm_list_check[0]:
            # Wait for app launch
            self.log.info('App({}) is in the pm list, wait 10 secs for app launched ...'.format(self.app_id))
            time.sleep(10)
            self.logcat_check = self.adb.executeShellCommand("logcat -d -s appmgr | grep {0}".format(self.app_id))[0]
        else:
            self.log.warning('App({}) is not in the pm list !'.format(self.app_id))
            self.logcat_check = self.adb.executeShellCommand("logcat -d -s appmgr | grep {0}".format(self.app_id))[0]

    def app_install_pass_criteria_check(self):
        check_list1 = ['app-install-success', 'app-install-request']
        if not self.pm_list_check[0] or not all(word in self.logcat_check for word in check_list1):
            raise self.err.TestFailure('APP({}) is not install successfully, test Failed !!!'.format(self.app_id))
        if 'app-install-failed' in self.logcat_check or 'download-and-install-failed' in self.logcat_check:
            if 'App installation in progress' in self.logcat_check:
                self.log.warning('There may have more than one user installation with the APP({}) running in parallel, '
                    'skip the app-install-failed check ...'.format(self.app_id))
            elif 'connection reset by peer' in self.logcat_check:
                self.log.error('connection reset by peer happened and retry installion 3 times if needed, '
                    'skip the app-install-failed or download-and-install-failed check ...')
            elif 'Failed to update the app catalog about app installation, so deleting the app' in self.logcat_check:
                self.log.warning('Failed to update the app catalog about app installation, the app has been deleted by app manager, '
                    'skip the download-and-install-failed check ...')
                if '502' in self.logcat_check: # cloud service 502 response
                    self.log.error('cloud return 502 found ...')
                elif 'EOF' in self.logcat_check:
                    self.log.error('cloud EOF happened ...')
            else:
                raise self.err.TestFailure('APP({}) is not install successfully, test Failed !!!'.format(self.app_id))
        # Launch app check
        self.timing.reset_start_time()
        while not self.timing.is_timeout(60*3):
            check_launch_app = self.adb.executeShellCommand('ps | grep {}'.format(self.app_id))[0]
            if check_launch_app:
                break
            self.log.warning('APP({}) not found in ps list, wait 10 secs and check again ...'.format(self.app_id))
            time.sleep(10)
            if self.timing.is_timeout(60*3):
                raise self.err.TestFailure('APP({}) is not launched successfully, test Failed !!!'.format(self.app_id))

    def check_appmgr_db_install(self):
        self.log.info('Start to check app manager database info ...')
        userID = self.uut_owner.get_user_id()
        db = self.adb.executeShellCommand("sqlite3 /data/wd/appmgr/db/index.db .dump | grep {0} | grep '{1}'"
            .format(self.app_id, userID))[0]
        while 'Text file busy' in db:
            db = self.adb.executeShellCommand("sqlite3 /data/wd/appmgr/db/index.db .dump | grep {0} | grep '{1}'"
                .format(self.app_id, userID))[0]
            time.sleep(1)
        count = 1
        while not db:
            self.log.warning('Not found userID({0}) with appID({1}) in appmgr database, wait for 5 secs and get again, try {2} times ...'
                .format(userID, self.app_id, count))
            time.sleep(5)
            db = self.adb.executeShellCommand("sqlite3 /data/wd/appmgr/db/index.db .dump | grep {0} | grep '{1}'"
                .format(self.app_id, userID))[0]
            count += 1
            if count == 5:
                raise self.err.TestFailure('The userID({0}) with appID({1}) is not in database, test Failed !!!'
                    .format(userID, self.app_id))

    def install_plex_app_kdp(self):
        # Check if the restsdk port changed again
        self.uut_owner.update_device_ip(port=self.uut_owner.detect_restsdk_port())
        self.timing.start()
        while not self.timing.is_timeout(self.timeout):
            successCode = self.uut_owner.install_app_kdp(app_id=self.app_id)
            if successCode == 204:
                break
            elif successCode == 409:
                self.log.warning('return code {}, send install app request again ...'.format(successCode))
            else:
                self.log.error('Install request response: {}, stop to send request ...'.format(successCode))
                break
            time.sleep(5)

        if not self.uut_owner.wait_for_app_install_completed(self.app_id):
            raise self.err.TestFailure('APP({}) is not install successfully, test Failed !!!'.format(self.app_id))
        self.log.info('App({}) has been installed.'.format(self.app_id))

    def check_plex_app_migration_status(self):
        user_id = self.uut_owner.get_user_id(escape=True)
        app_pref_cmd = "cat /data/wd/diskVolume0/kdpappmgr/config/com.plexapp.mediaserver.smb/" + user_id + \
                       "/Plex\ Media\ Server/Preferences.xml"
        app_preference = self.ssh_client.execute_cmd(app_pref_cmd, quiet=True)[0]
        if "OldestPreviousVersion" in app_preference:
            self.log.info("** Plex app previous version info is found in the preferences.xml")
        else:
            raise self.err.TestFailure('Cannot find the plex app previous version info in the preferences.xml!')

        app_logs = self.ssh_client.execute_cmd("cat /var/log/appMgr.log", quiet=True)[0]
        check_list = ["copyOldConfig start", "copyOldConfig finish"]
        if all(word in app_logs for word in check_list):
            self.log.info("** Plex app copy config keywords are found in appMgr.log")
        else:
            raise self.err.TestFailure('Cannot find the plex app copy config keywords in the appMgr.log!')

    """ Utilities """
    def restart_otaclient(self):
        self.log.info("Restarting otaclient...")
        self.adb.executeShellCommand('stop otaclient', consoleOutput=False)
        time.sleep(10)
        self.adb.executeShellCommand('start otaclient', consoleOutput=False)

    def download_precontent_files_to_plex_folder(self):
        self.log.info('Download pre-content files to plex app folder ...')
        user_id = self.uut_owner.get_user_id(escape=True)
        download_url = 'http://{}/test/AppManagerDataSetUse/'.format(self.file_server_ip)
        test_device_path = '/data/wd/diskVolume0/restsdk/userRoots/{}/Plex/AppManagerDataSetUse/'.format(user_id)
        self.adb.download_files_and_upload_to_test_device(
            download_url=download_url, test_device_path=test_device_path, is_folder=True, local_path='AppManagerDataSetUse')

    def check_precontent_files_after_migration(self):
        self.log.info('Check pre-content files is still exist after app migration ...')
        user_id = self.uut_owner.get_user_id(escape=True)
        precontent_path = '{0}/{1}/Plex/AppManagerDataSetUse'.format(KDP.USER_ROOT_PATH, user_id)
        self.ssh_client.execute('ls {}'.format(precontent_path))
        if not self.ssh_client.check_file_in_device(precontent_path):
            raise self.err.TestFailure("Pre-content folder({}) is not exist, test failed!!".format(precontent_path))


    """ Utilities """
    def safe_unzip(self, zip_file, extractpath='.'):
        self.log.info('Start unzip file')
        with zipfile.ZipFile(zip_file, 'r') as zf:
            for member in zf.infolist():
                abspath = os.path.abspath(os.path.join(extractpath, member.filename))
                if abspath.startswith(os.path.abspath(extractpath)):
                    zf.extract(member, extractpath)

    def firmware_md5_checksum_compare(self):
        self.log.info("Comparing the md5 checksum of downloaded firmware")
        exist_md5_result = self.ssh_client.check_file_in_device(self.fw_image_path_on_device + '.md5')
        if exist_md5_result:
            md5_expect = self.ssh_client.execute_cmd("cat {0}.md5".format(self.fw_image_path_on_device))[0].rstrip("\n")
            md5_image = self.ssh_client.execute_cmd("busybox md5sum {0}".format(self.fw_image_path_on_device))[0].split()[0]
            self.log.info("Firmware Image MD5: {}".format(md5_image))
            if md5_expect != md5_image:
                raise self.err.TestFailure("The firmware image MD5 should be {}, but it's {}!".format(md5_expect, md5_image))
            else:
                self.log.info("Firmware image MD5 checksum comparison PASS!")
                return True
        else:
            self.log.warning('{} is not in the device, cannot compare the firmware image checksum'
                             .format(self.fw_image_path_on_device + '.md5'))
            return False

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Firmware Update Utility Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/firmware_update.py --uut_ip 10.92.224.68 --firmware_version 4.1.0-725 --cloud_env dev1\
        """)

    # Test Arguments
    parser.add_argument('--file_server_ip', default='fileserver.hgst.com', help='File server IP address')
    parser.add_argument('--local_image', action='store_true', help='Download firmware image from local file server')
    parser.add_argument('--app_id', default='com.plexapp.mediaserver.smb', help='App ID to installed')
    parser.add_argument('--local_image_path', default=None, help='Specify the absolute path of local firmware image')
    parser.add_argument('--ota_bucket_id', help='Choose "default", "special" buckets or specify the bucket id',
                        default='default')
    args = parser.parse_args()

    test = Ota_Android_To_Linux(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp or resp is None:
        sys.exit(0)
    sys.exit(1)
