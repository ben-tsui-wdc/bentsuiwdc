# -*- coding: utf-8 -*-
""" Test cases to check Logs are uploaded before device reboot.
"""
__author__ = "Ben Lin <ben.lin@wdc.com>"

# std modules
import sys
import time
import datetime
import argparse
import os

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.sumologicAPI import sumologicAPI
from platform_libraries.adblib import ADB

class SumologicUploadBeforeReboot(TestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Logs are uploaded before device reboot'
    # Popcorn
    TEST_JIRA_ID = 'KAM-26712'

    SETTINGS = {
        'uut_owner': True
    }
    TEST_FILE = 'TEST_DB_LOCK.png'

    start = time.time()

    def declare(self):
        self.timeout = 300

    def before_test(self):
        self.environment = self.uut.get('environment')
        self.pip = True
        self.url_exist = False
        self.holding = True
        self.sumoURL = ""
        self.logname = ""
        self.jobID = ""
        self.counter = 0

        if os.path.isfile(self.TEST_FILE):
            os.remove(self.TEST_FILE)

    def test(self):
        # Skip test because dev1 environment has no hash mac address
        if self.environment == 'dev1':
            raise self.err.TestSkipped('Environment is {}, skipped the test !!'.format(self.environment))

        self.check_device_bootup()
        self.uut_owner.enable_pip()
        self.sumologicAPI = sumologicAPI()

        MAX_RETRIES = 5
        retry = 1
        while retry <= MAX_RETRIES:
            self.mac_address_hash = self.adb.get_hashed_mac_address()
            if not self.mac_address_hash:
                self.log.warning("Failed to get mac address, remaining {} retries".format(retry))
                time.sleep(10)
                retry += 1
            else:
                break

        # Upload files
        self.log.info('Try to upload a new file by device owner')
        self._create_random_file(self.TEST_FILE)
        with open(self.TEST_FILE, 'rb') as f:
            self.uut_owner.chuck_upload_file(file_object=f, file_name=self.TEST_FILE)
        user_id = self.uut_owner.get_user_id(escape=True)
        if self.adb.check_file_exist_in_nas("{}".format(self.TEST_FILE), user_id):
            self.log.info('Upload test file to device successfully!')
        else:
            raise self.err.TestFailure('Upload test file to device failed!')

        count = 1
        while count <= 4:
            touch_log_name = "reboot-log-upload-test0{}".format(count)
            self.adb.executeShellCommand('echo "{}" >> /data/logs/wdlog-safe.log'.format(touch_log_name))

            self.uut_owner.reboot_device()
            self.log.info('Expect device do rebooting ...')
            if not self.adb.wait_for_device_to_shutdown():
                raise self.err.TestFailure('Device rebooting Failed !!')
            self.log.info('Device rebooting ...')
            if self.wait_device():
                self.log.info('Device bootup completed.')
            else:
                raise self.err.TestFailure('Device bootup Failed in {}s !!'.format(self.timeout))

            # search "reboot-log-upload-test01" on sumologic
            sumo_des = '_sourceName={} AND {}'.format(self.mac_address_hash, touch_log_name)
            self.log.info("Searching rules: %s" %sumo_des)

            try:
                self.result = self.sumologicAPI.searchRQ(_adb_client=self.adb, searching=sumo_des, relativeTime=10, timezone="GMT")
                self.counter = int(self.result["messageCount"])
                self.log.info(self.result)
            except Exception as ex:
                self.log.error("Failed to send sumologic API: {}".format(ex))
                raise self.err.TestFailure("Test failed related to sumologicAPI method.")

            if self.counter <= 0:
                self.log.error("Test: Failed. Cannot find the log in sumologic website.")
                raise self.err.TestFailure("Test: Failed, log file is not found in sumologic database.")
            else:
                self.log.info("Test: pass")

            count += 1

            if count == 5:
                self.log.info("Test: Done")
                break

            self.log.info("Wait 1 min for next test ...")
            time.sleep(60)

    def after_test(self):
        if os.path.isfile(self.TEST_FILE):
            os.remove(self.TEST_FILE)

    def _create_random_file(self, file_name, local_path='', file_size='1048576'):
        # Default 1MB dummy file
        self.log.info('Creating file: {}'.format(file_name))
        try:
            with open(os.path.join(local_path, file_name), 'wb') as f:
                f.write(os.urandom(int(file_size)))
        except Exception as e:
            self.log.error('Failed to create file: {0}, error message: {1}'.format(local_path, repr(e)))
            raise

    def wait_device(self):
        self.log.info('Wait for device boot completede...')
        timeout = 60*10
        adb = ADB(uut_ip=self.env.uut_ip)
        if not adb.wait_for_device_boot_completed(timeout=timeout):
            self.log.error('Device seems down.')
            return False
        adb.disconnect()
        return True
        
    def check_device_bootup(self):
        # check device boot up
        while not self.is_timeout(self.timeout):
            if self.adb.check_platform_bootable():
                self.log.info('Boot completed')
                break
            time.sleep(5)

    def is_timeout(self, timeout):
        return time.time() - self.start >= timeout

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Logs are uploaded before device reboot Check Script ***
        Examples: ./run.sh functional_tests/sumologic_upload_log_before_reboot.py --uut_ip 10.92.224.68\
        """)

    test = SumologicUploadBeforeReboot(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
