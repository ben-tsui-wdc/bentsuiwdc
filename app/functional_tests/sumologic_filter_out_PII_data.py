# -*- coding: utf-8 -*-
""" Test cases to check Uploaded device logs filter out PII data.
"""
__author__ = "Ben Lin <ben.lin@wdc.com>"

import sys
import time
import datetime
import argparse
import json

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.sumologicAPI import sumologicAPI
from bat_scripts_new.usb_auto_mount import UsbAutoMount
from bat_scripts_new.usb_slurp_backup_file import UsbSlurpBackupFile

class SumologicFilterOutPIIData(TestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Uploaded device logs filter out PII data'
    # Popcorn
    TEST_JIRA_ID = 'KAM-18971'

    SETTINGS = {
        'uut_owner': True
    }

    start = time.time()
    timeout = 300

    def before_test(self):
        self.environment = self.uut.get('environment')
        self.pii_mac_address = self.adb.get_mac_address(interface='wlan0')
        self.pii_user_id = self.uut_owner.get_user_id()
        self.pii_device_id, self.pii_security_code, self.pii_local_code, date_time = self.uut_owner.get_local_code_and_security_code()
        self.mount_path = '/mnt/media_rw/'

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

        self.log.info("mac_address_hash: {}".format(self.mac_address_hash))
        self.log.info("pii_mac_address: {}".format(self.pii_mac_address))
        self.log.info("pii_user_id: {}".format(self.pii_user_id))
        self.log.info("pii_device_id: {}".format(self.pii_device_id))
        self.log.info("pii_security_code: {}".format(self.pii_security_code))
        self.log.info("pii_local_code: {}".format(self.pii_local_code))

    def test(self):
        # Skip test because dev1 environment has no hash mac address
        if self.environment == 'dev1':
            raise self.err.TestSkipped('Environment is {}, skipped the test !!'.format(self.environment))

        self.check_device_bootup()
        self.adb.reboot_device_and_wait_boot_up()
        self.uut_owner.enable_pip()
        self.adb.clean_logcat()

        usb_info = self.uut_owner.get_usb_info()
        self.usb_id = usb_info.get('id')
        self.usb_name = usb_info.get('name')
        self.log.info('USB Name: {}'.format(self.usb_name))
        self.log.info('USB ID: {}'.format(self.usb_id))

        UsbAutoMount(self).test()
        UsbSlurpBackupFile(self).test()
        self.usb_mount = self.adb.executeShellCommand('ls {}'.format(self.mount_path))[0].split()[0]
        usb_path = '{0}{1}/'.format(self.mount_path, self.usb_mount)
        usb_files = self.adb.executeShellCommand('find %s -type f -exec basename {} \;' %usb_path)[0]
        lists = [path.split(usb_path).pop() for path in usb_files.split()]
        file_list_str = '" OR "'.join(lists)
        file_list_str = '"{}"'.format(file_list_str)
        self.log.info("file_list string: {}".format(file_list_str))


        # Do reboot and waiting log upload to SumoLogic
        self.adb.reboot_device_and_wait_boot_up()

        sumo_des = '(_sourceName={}) AND ("{}" OR "{}" OR "{}" OR "{}" OR "{}")'.format(
            self.mac_address_hash,
            self.pii_mac_address,
            self.pii_user_id,
            self.pii_device_id,
            self.pii_security_code,
            self.pii_local_code
        )
        sumo_des = sumo_des.replace('"', '\\"')
        self.log.info('sumo_des: {}'.format(sumo_des))
        counter = self.sumologic_search(sumo_des=sumo_des)
        if counter > 0:
            raise self.err.TestFailure("Find PII data in Sumologic!")

        sumo_des = '(_sourceName={}) AND ({})'.format(self.mac_address_hash, file_list_str)
        sumo_des = sumo_des.replace('"', '\\"')
        counter = self.sumologic_search(sumo_des=sumo_des)
        if counter > 0:
            raise self.err.TestFailure("Find USB info in Sumologic!")

    def sumologic_search(self, sumo_des=None):
        try:
            sumologic = sumologicAPI()
            self.result = sumologic.searchRQ(_adb_client=self.adb, searching=sumo_des, relativeTime=10, timezone="GMT")
            counter = int(self.result["messageCount"])
            self.log.info(self.result)
        except Exception as ex:
            self.log.error("Failed to send sumologic API: {}".format(ex))
            raise self.err.TestFailure("Test failed related to sumologicAPI method.")

        return counter

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
        *** Uploaded device logs filter out PII data Check Script ***
        Examples: ./run.sh functional_tests/sumologic_filter_out_PII_data.py --uut_ip 10.92.224.68\
        """)

    test = SumologicFilterOutPIIData(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
