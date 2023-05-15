# -*- coding: utf-8 -*-
""" Test case for Device Reboot
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from godzilla_scripts.restsdk_bat_scripts.upload_data import UploadDataTest
from godzilla_scripts.bat_scripts.samba_rw_check import SambaRW


class Reboot(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Device Reboot Test'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1020'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.no_rest_api = False
        self.no_wait = False
        self.io_before_test = False
        self.idle_time = 180

    def init(self):
        self.timeout = 60*20

    def test(self):
        if self.io_before_test:
            self.log.info("Run some IO before testing")
            smbrw = SambaRW(self)
            smbrw.keep_test_data = True
            smbrw.before_test()
            smbrw.test()
            smbrw.after_test()
            if self.idle_time > 0:
                self.log.info("Wait for {} seconds after IO".format(self.idle_time))
                time.sleep(self.idle_time)

        if self.no_rest_api:
            self.log.info("Run device reboot by SSH and command line")
            self.ssh_client.reboot_device()
        else:
            device_id_before = self.uut_owner.get_local_code_and_security_code()[0]
            self.log.info("Checking the device id before testing: {}".format(device_id_before))
            self.log.info("Run device reboot by RestSDK API")
            if self.ssh_client.check_file_in_device('/tmp/system_ready'):
                self.ssh_client.execute_cmd('rm /tmp/system_ready')
            self.uut_owner.reboot_device()

        self.log.info('Expect device reboot complete in {} seconds.'.format(self.timeout))
        start_time = time.time()
        if not self.ssh_client.wait_for_device_to_shutdown(timeout=self.timeout):
            raise self.err.TestFailure('Device was not shut down successfully!')

        if not self.no_wait:
            if not self.ssh_client.wait_for_device_boot_completed(timeout=self.timeout):
                raise self.err.TestFailure('Device was not boot up successfully!')

            if not self.no_rest_api:
                if not self.ssh_client.get_restsdk_service():
                    raise self.err.TestFailure('RestSDK service was not started after device reboot!')

                self.uut_owner.wait_until_cloud_connected(timeout=self.timeout)

                device_id_after = self.uut_owner.get_local_code_and_security_code()[0]
                self.log.info("Checking the device id after testing: {}".format(device_id_after))
                if device_id_before != device_id_after:
                    raise self.err.TestFailure('Device ID is not match, reboot test failed!')

            # Todo: upload a file after testing
            """
            self.log.info("Try to run a simple file upload test after device boot up")
            upload_data_test = UploadDataTest(parser)
            upload_data_test.main()
            """
        self.log.warning("Reboot complete in {} seconds".format(time.time() - start_time))
        if (time.time() - start_time) > 600:  # reboot should be completed in 10 mins
            self.log.warning("The ssh will be disconnected before reboot process in some GZA device, " +
                             "need to wait the device to shutdown again")
            start_time = time.time()
            if not self.ssh_client.wait_for_device_to_shutdown(timeout=self.timeout):
                raise self.err.TestFailure('Device was not shut down successfully!')

            if not self.no_wait:
                if not self.ssh_client.wait_for_device_boot_completed(timeout=self.timeout):
                    raise self.err.TestFailure('Device was not boot up successfully!')
            self.log.warning("Reboot complete in {} seconds".format(time.time() - start_time))

    def after_test(self):
        self.log.info("Reconnect SSH protocol after testing")
        self.ssh_client.connect()
        if self.io_before_test:
            self.log.info("Clean the IO test file")
            file_name = "test50MB"  # the dummy test file in the samrw test
            if self.ssh_client.check_file_in_device("/shares/Public/{}".format(file_name)):
                self.ssh_client.execute_cmd("rm /shares/Public/{}".format(file_name))


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Reboot test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/reboot.py --uut_ip 10.136.137.159 -wait\
        """)
    parser.add_argument('-nowait', '--no_wait', help='Skip waiting for device boot up completed', action='store_true')
    parser.add_argument('-noapi', '--no_rest_api', help='Not use restapi to reboot device', action='store_true')
    parser.add_argument('--io_before_test', help='Use samba to run IO before testing', action='store_true')
    parser.add_argument('--idle_time', help='idle time after io', default=180)

    test = Reboot(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
