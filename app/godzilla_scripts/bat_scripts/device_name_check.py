# -*- coding: utf-8 -*-
""" Test case to check the device name
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class DeviceNameCheck(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Device Name Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1579'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        expect_model = self.uut.get('model')
        current_model = self.ssh_client.get_model_name()
        self.log.info("Expect model: {}".format(expect_model))
        self.log.info("Current model: {}".format(current_model))
        if expect_model != current_model:
            raise self.err.TestFailure('Current model: {0} is not expect model: {1}!'.
                                       format(current_model, expect_model))

if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Device Name Check test on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/device_name_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = DeviceNameCheck(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
