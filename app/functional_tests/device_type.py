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


class DeviceType(TestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'DeviceType'
    # Popcorn
    TEST_JIRA_ID = 'KAM-21415'


    def declare(self):
        pass


    def test(self):
        for element in self.uut_owner.get_devices_info_per_specific_user():
            if element.get('deviceId') == self.uut_owner.device_id:
                product = self.adb.getModel()
                if element.get('type') != product:
                    raise self.err.TestFailure('The prodcut type is <{0}> by adb, but cloud API returns <{1}>.'.format(product, element.get('type')))
                break


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Test of device type confirmation by Cloud API on Kamino ***
        Examples: ./run.sh functional_tests/device_type.py --uut_ip 10.92.224.71 --cloud_env qa1 --dry_run --debug_middleware\
        """)

    test = DeviceType(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)