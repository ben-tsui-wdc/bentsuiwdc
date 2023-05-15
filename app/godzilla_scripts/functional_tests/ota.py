# -*- coding: utf-8 -*-
""" JIRA Ticket of test steps: TBD
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
import pprint
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from platform_libraries.cloud_api import CloudAPI
from godzilla_scripts.bat_scripts.firmware_update import FirmwareUpdate
from platform_libraries.constants import Godzilla as GZA
from godzilla_scripts.bat_scripts.factory_reset import FactoryReset


class OTA(GodzillaTestCase):

    TEST_SUITE = 'Platform Functional Tests'
    TEST_NAME = 'OTA Test'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-2321'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None
    REPORT_NAME = 'OTA'

    SETTINGS = {
        'enable_auto_ota': True
    }

    def init(self):
        self.cloud = CloudAPI(env=self.env.cloud_env)

    def before_test(self):
        self.log.info("Restart RestSDK service if it's in minimal mode")
        self.ssh_client.disable_restsdk_minimal_mode()

    def test(self):
        self.log.info("Step 1: Downgrade the firmware to {}".format(self.start_fw))
        firmware_update = FirmwareUpdate(parser)
        firmware_update.fw_version = self.start_fw
        firmware_update.keep_fw_img = self.keep_fw_img
        firmware_update.skip_checksum_check = self.skip_checksum_check
        firmware_update.force_update = True
        firmware_update.before_test()
        firmware_update.test()
        firmware_update.after_test()

        self.log.info("Step 2: Run factory reset after firmware downgrade")
        factory_reset = FactoryReset(parser)
        factory_reset.test()

        self.ssh_client.connect()
        local_version = self.ssh_client.get_firmware_version()
        if local_version != self.start_fw:
            raise self.err.TestFailure("Check if the downgrade step was failed!")

        self.log.info("Step 3: Check if the device id is in the OTA bucket and check device status")

        result = self.get_ota_status_with_retries()
        self.log.info("Original OTA status:")
        pprint.pprint(result)

        if self.ota_bucket_id.lower() == "default":
            self.log.info("Use default OTA bucket for testing")
            device_info = GZA.DEVICE_INFO.get(self.env.model)
            if self.env.cloud_env == "dev1":
                ota_default_bucket = device_info.get("ota_default_bucket_dev1")
            elif self.env.cloud_env == "qa1":
                ota_default_bucket = device_info.get("ota_default_bucket_qa1")
            elif self.env.cloud_env == "prod":
                ota_default_bucket = device_info.get("ota_default_bucket_prod")
            self.cloud.add_device_in_ota_bucket(ota_default_bucket, [self.uut_owner.get_device_id()])
        elif self.ota_bucket_id and self.ota_bucket_id != result.get('bucketId'):
            self.log.info("Bucket id not match, updating the specified bucket id: {} in the cloud OTA status".
                          format(self.ota_bucket_id))
            self.cloud.add_device_in_ota_bucket(self.ota_bucket_id, [self.uut_owner.get_device_id()])
        elif self.ota_bucket_id == "DEVICE_VERSION":
            """
            If bucket id is "DEVICE_VERSION", that means device is even not in the default bucket,
            and beta users will not able to be ota forever
            """
            self.log.info("The bucket id was abnormal status (DEVICE_VERSION), change it to the default bucket")
            device_info = GZA.DEVICE_INFO.get(self.env.model)
            self.cloud.add_device_in_ota_bucket(device_info.get("ota_default_bucket"), [self.uut_owner.get_device_id()])

        result = self.get_ota_status_with_retries()
        self.log.info("Updated OTA status:")
        pprint.pprint(result)

        self.log.info("Step 4: Wait for device to be OTA to new version")
        ota_started = False
        ota_retry_delay = 30
        restart_otaclient_count = 0
        self.log.info("OTA timeout = {} seconds".format(self.ota_timeout))
        self.log.info("OTA retry delay = {} seconds".format(ota_retry_delay))
        for i in range(0, int(self.ota_timeout/ota_retry_delay)):
            result = self.get_ota_status_with_retries()
            current_version = result.get('currVersion')
            sent_version = result.get('sentVersion')
            ota_status = result.get('status')
            self.test_fw = sent_version
            self.log.info("cloud currVersion: {}".format(current_version))
            self.log.info("cloud sentVersion: {}".format(sent_version))
            self.log.info("OTA started: {}".format(ota_started))
            if current_version != self.start_fw and not ota_started:
                self.log.info("Waiting for the current version updated to start_fw: {} in the cloud".format(self.start_fw))
            elif not sent_version:
                self.log.warning("The cloud sentVersion is: {}, keep waiting for the clouds to be updated".format(sent_version))
            else:
                if not ota_started:
                    self.ssh_client.ota_update_firmware_now()
                    self.log.info("OTA start running, current_fw: {0}, sent_fw: {1}".
                                  format(current_version, sent_version))
                    ota_started = True
                if ota_status == "updateOk":
                    self.log.info("OTA complete, checking firmware version and device status")
                    if current_version != sent_version:
                        if i == int(self.ota_timeout / ota_retry_delay):
                            self.log.error("OTA current_version doesn't match sent_version after {} seconds!".
                                           format(self.ota_timeout))
                            raise self.err.TestFailure("Expect firmware version: {0}, current firmware version: {1}".
                                                       format(sent_version, current_version))
                        else:
                            self.log.warning("OTA current_version doesn't match sent_version, retry after {} seconds".
                                             format(ota_retry_delay))
                    else:
                        self.ssh_client.wait_for_device_boot_completed()
                        break
                else:
                    if i == int(self.ota_timeout/ota_retry_delay):
                        raise self.err.TestFailure("OTA status is still not 'updateOk' after {} secs!".format(self.ota_timeout))
                    self.log.info("OTA status is: {}, keep waiting...".format(ota_status))
                    if ota_status == "SENT_TO_DEVICE":
                        if restart_otaclient_count == 10:
                            self.log.info("Try to restart the OTA client to update the OTA status")
                            self.ssh_client.restart_otaclient()
                            restart_otaclient_count = 0
                        else:
                            restart_otaclient_count += 1
            time.sleep(ota_retry_delay)

        self.log.info("After OTA update, restart RestSDK service if it's in minimal mode")
        self.ssh_client.disable_restsdk_minimal_mode()
        
        self.log.info("Step 5: Verify the current firmware version")
        local_version = self.ssh_client.get_firmware_version()
        if local_version != self.test_fw:
            raise self.err.TestFailure("Expect firmware version: {0}, current firmware version: {1}".
                                       format(self.test_fw, local_version))
        else:
            self.log.info("OTA test is PASSED!")

    def after_test(self):
        if int(self.loop_interval) > 0:
            self.log.info("Sleep {} seconds between each iteration".format(self.loop_interval))
            time.sleep(int(self.loop_interval))
            if self.check_standby:
                if int(self.loop_interval) >= (20*60):
                    # HDD will enter standby mode only after 20 mins
                    result = self.ssh_client.check_hdd_in_standby_mode()
                    if not result:
                        raise self.err.TestFailure("Device didn't enter standby mode after {} seconds".
                                                   format(self.loop_interval))
                else:
                    self.log.info("The loop inverval is less than 20 min so skip standby mode check")

    def after_loop(self):
        # This is for Jenkins to update test_fw version if it's auto
        with open("output/ota_version.txt", "w") as f:
            f.write("OTA_FW={}\n".format(self.test_fw))

    def get_ota_status_with_retries(self):
        device_id = self.uut_owner.get_local_code_and_security_code()[0]
        cloud_retries_delay = 60
        cloud_retries_max = int(self.ota_timeout/cloud_retries_delay)
        cloud_retries = 0
        while cloud_retries < cloud_retries_max:
            result = self.cloud.get_ota_status(device_id).get('data')
            if not result:
                if cloud_retries == cloud_retries_max:
                    raise self.err.TestFailure(
                        "Cannot get the OTA information in {} minutes!".format(cloud_retries_max))

                self.log.warning("Cannot get the OTA information from the cloud! Wait for {} secs to retry, "
                                 "{} retries left...".format(cloud_retries_delay, cloud_retries_max - cloud_retries))
                cloud_retries += 1
                time.sleep(cloud_retries_delay)
            else:
                return result


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Get_Device_info test on Kamino Android ***
        Examples: ./run.sh godzilla_scripts/functional_tests/ota.py --uut_ip 10.136.137.159:8001 \
                  -env dev1 -lt 3 --local_image --start_fw 3.00.6 --test_fw 3.00.11
        """)
    parser.add_argument('--start_fw', help='Start firmware version, ex. 3.10.121', default='3.10.121')
    parser.add_argument('--usb_folder', help='Use the data set in USB drive, if it is None then download data set from file server')
    parser.add_argument('--file_server_ip', help='File server IP address', default='fileserver.hgst.com')
    parser.add_argument('--dir_in_file_server', help='The data set dir in file server', default='/test/IOStress/')
    parser.add_argument('--private_network', action='store_true', default=False,
                        help='The test is running in private network or not, it is related to the file server')
    parser.add_argument('--local_image', action='store_true', default=False,
                        help='Download ota firmware image from local file server')
    parser.add_argument('--ota_timeout', help='The maximum ota timeout value', type=int, default=3600)
    parser.add_argument('--keep_fw_img', action='store_true', default=False, help='Keep downloaded firmware')
    parser.add_argument('--ota_bucket_id', help='Specified bucket id', default="default")
    parser.add_argument('--loop_interval', help='sleep time between each iteration', default=0)
    parser.add_argument('--check_standby', help='check if device enter standby mode if loop_interval is specified',
                        action='store_true', default=False)
    parser.add_argument('-scc', '--skip_checksum_check', help='skip the fw image checksum comparison',
                        action='store_true')
    # parser.add_argument('--clean_restsdk_db', help='Clear restsdk database', action='store_true', default=False)

    test = OTA(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
