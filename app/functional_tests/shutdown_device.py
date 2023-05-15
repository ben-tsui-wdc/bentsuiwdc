# -*- coding: utf-8 -*-
""" Test cases for KAM-7875: Power State - Power Up after Graceful Shutdown.
"""
__author__ = "Fish Chiang <fish.chiang@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.adblib import ADB
from platform_libraries.common_utils import create_logger
from platform_libraries.inventoryAPI import InventoryAPI, InventoryException
from platform_libraries.powerswitchclient import PowerSwitchClient

class ShutdownDevice(TestCase):

    TEST_SUITE = 'Functional Test'
    TEST_NAME = 'Shutdown Device'
    # Popcorn
    TEST_JIRA_ID = 'KAM-7875'

    def test(self):
        is_device_shutdown = self.uut_owner.shutdown_device()
        time.sleep(5)
        self.verify_result(is_device_shutdown)

    def verify_result(self, is_device_shutdown):
        if not is_device_shutdown:
            self.log.error('Shutdown device: FAILED.')
            raise self.err.TestFailure('Shutdown device failed')
        timeout = 60
        self.log.info('Expect device do shutdown in {}s.'.format(timeout))
        if not self.adb.wait_for_device_to_shutdown(timeout=timeout):
            self.log.error('Shutdown device: FAILED.')
            raise self.err.TestFailure('Shutdown device failed')
        self.log.info('Shutdown device: PASSED.')
        # Power off
        self.log.info("Powering off the device")
        self.power_switch.power_off(self.env.power_switch_port)
        self.adb.connected = False
        time.sleep(30)  # interval between power off and on
        # Power on
        self.log.info("Powering on the device")
        self.power_switch.power_on(self.env.power_switch_port)
        time.sleep(90)  # Sleep 90 secs and then check the bootable flag
        if not self.adb.wait_for_device_boot_completed():
            self.log.error('Power Up after Graceful Shutdown: FAILED, the device seems down.')
            raise self.err.TestFailure('Power Up after Graceful Shutdown: FAILED, the device seems down.')
        self.log.info('Power Up after Graceful Shutdown: PASSED.')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Shutdown_Device test on Kamino Android ***
        Examples: ./run.sh functional_tests/shutdown_device.py --uut_ip 192.168.11.115\
        """)

    test = ShutdownDevice(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
