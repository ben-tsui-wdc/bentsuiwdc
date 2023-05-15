# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import os
import re
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class SystemTimeAfterReboot(TestCase):
    '''
    Test Case: https://jira.wdmv.wdc.com/browse/KAM-27550
    '''
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'SystemTimeAfterReboot'
    # Popcorn
    TEST_JIRA_ID = 'KAM-27550'

    def declare(self):
        self.timeout = 600

    def test(self):
        # Get the system from script client
        stdout, stderr = self.adb.executeCommand('date +%Y%m%d')
        stdout_client = stdout.strip()
        # Get the system from testing device
        stdout, stderr = self.adb.executeShellCommand('date +%Y%m%d')
        stdout_device = stdout.strip()
        if stdout_client != stdout_device:
            raise self.err.TestFailure('Systen time of stdout_device is not correct.\
             \nSystem time of client: {}\nSystem time of device: {}'.format(stdout_client, stdout_device))
        
        # Check system time of device after rebooting device but NTP sync is not completed.
        # 1. Remove the wifi configuration before rebooting
        network = self.serial_client.get_network(self.env.ap_ssid)
        network_id = network[0]
        self.serial_client.disable_network(network_id)
        self.serial_client.remove_network(network_id, save_changes=True, restart_wifi=False)
        self.serial_client.reboot_device(timeout=self.timeout)
        self.serial_client.wait_for_boot_complete()
        self.serial_client.serial_write("system_time=DATEis`date +%Y%m%d` && echo $system_time")
        # 2. Record the system_time
        stdout = self.serial_client.serial_filter_read('DATEis')
        self.log.info(stdout[1])
        stdout_device = stdout[1].split('DATEis')[1].strip()
        # 3. Add the wifi
        self.serial_client.add_wifi(self.env.ap_ssid, self.env.ap_password)
        # 4. Check system_time
        if stdout_device == '20180401':
            raise self.err.TestFailure('System time of device is reset to default time 2018-04-01 after rebooting.')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Confirm system time is correct after device reboot ***
        Examples: ./run.sh functional_tests/system_time_after_reboot.py --uut_ip 10.92.224.71 --cloud_env qa1 --dry_run --debug_middleware\
        """)

    test = SystemTimeAfterReboot(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)