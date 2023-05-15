# -*- coding: utf-8 -*-
""" Test cases for KAM-8766
    [LED] Firmware update
    Check LED should solid and 100% light, when system is updating firmware
"""

__author__ = "Fish Chiang <fish.chiang@wdc.com>"

# std modules
import os
from subprocess import check_output
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from functional_tests.update_fw_to_same_version import UpdateFWToSameVersion

class LEDCheckUpdateFW(TestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'led_fw_update_check'
    # Popcorn
    TEST_JIRA_ID = 'KAM-8766'
    SETTINGS = {'uut_owner': True, 'power_switch': False}

    def test(self):
        fw_update = UpdateFWToSameVersion(self)
        fw_update.local_image = self.local_image
        fw_update.run_test()
        self.led_state = fw_update.get_serial_led()
        self.log.info('led_state={}'.format(self.led_state))
        if self.led_state != 'Full Solid':
            raise self.err.TestFailure('Check LED should "Full solid" when system is updating firmware: FAILED')
        self.log.info('Check system log: LED is "Full Solid"')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Check LED should full solid, when system is updating firmware Script ***
        Examples: ./run.sh functional_tests/led_fw_update.py --uut_ip 10.92.224.61 --dry_run --debug_middleware --local_image\
        """)
    parser.add_argument('--file_server', help='File server IP address', default='fileserver.hgst.com')
    parser.add_argument('--local_image', action='store_true', default=False,
                        help='Download ota firmware image from local file server')

    test = LEDCheckUpdateFW(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)