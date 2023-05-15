# -*- coding: utf-8 -*-
""" Test cases for KAM-7873: Power State - Lost Power from Ready mode
"""
__author__ = "Fish Chiang <fish.chiang@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase

class LostPower(TestCase):

    TEST_SUITE = 'Functional Test'
    TEST_NAME = 'Lost Power Test'
    # Popcorn
    TEST_JIRA_ID = 'KAM-7873'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        self.log.info("Powering off the device")
        self.power_switch.power_off(self.env.power_switch_port)
        self.adb.connected = False
        time.sleep(30)  # interval between power off and on
        self.log.info("Powering on the device")
        self.power_switch.power_on(self.env.power_switch_port)
        self.log.info("Wait for reboot process complete")
        time.sleep(90)  # Sleep 90 secs and then check the bootable flag

        if not self.adb.wait_for_device_boot_completed():
            self.log.error('Timeout({}secs) to wait device boot completed..'.format(self.timeout))
            raise self.err.TestFailure('Lost Power Test: FAILED')

        self.log.info("Lost Power Test: PASSED.")
if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Power_On_Off test on Kamino Android ***
        Examples: ./run.sh functional_tests/lost_power_test.py --uut_ip 192.168.11.115\
        """)

    test = LostPower(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
