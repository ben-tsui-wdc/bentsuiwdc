# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: POST /v2/system/reset - 200
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import os
import sys
# platform modules
from kdp_scripts.nasadmin_tests.others.erase_settings_test import EraseSettingsTest
from kdp_scripts.test_utils.test_case_utils import nsa_add_argument_2nd_user
from middleware.arguments import KDPInputArgumentParser


class SystemReset(EraseSettingsTest):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Initiate system reset'
    # Popcorn
    TEST_JIRA_ID = 'KDP-4970'

    def reset_step(self):
        self.log.info('Erasing device settings')
        self.nasadmin.system_reset(rtype="eraseSettings")


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** System reset test ***
        """)
    nsa_add_argument_2nd_user(parser)

    test = SystemReset(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
