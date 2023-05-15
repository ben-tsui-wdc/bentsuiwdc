# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"
__compatible__ = 'KDP,RnD'

# std modules
import os
import re
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class DeviceType(KDPTestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-405 - DeviceType'
    # Popcorn
    TEST_JIRA_ID = 'KDP-405'

    def declare(self):
        pass

    def test(self):
        for element in self.uut_owner.get_devices_info_per_specific_user():
            if element.get('deviceId') == self.uut_owner.device_id:
                self.log.info('DEVICE ID: {}'.format(self.uut_owner.device_id))
                self.log.info('DEVICE INFO: {}'.format(element))
                product = self.ssh_client.get_model_name()
                if element.get('type') != product:
                    raise self.err.TestFailure('The prodcut type is <{0}> by SSH, but cloud API returns <{1}>.'.format(product, element.get('type')))
                break

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Test of device type confirmation by Cloud API on Kamino ***
        Examples: ./run.sh kdp_scripts/functional_tests/device_type.py --uut_ip 10.92.224.71 --cloud_env qa1 --dry_run --debug_middleware\
        """)

    test = DeviceType(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)