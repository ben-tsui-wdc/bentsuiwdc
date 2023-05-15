# -*- coding: utf-8 -*-
""" Test cases to check firmware update is succeed.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class FWUpdatePASSCheck(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Firmware Update Utility Test'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-13986,KAM-15038'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        fw_current_ver = self.adb.getFirmwareVersion()
        if self.version_check != fw_current_ver:
            raise self.err.TestFailure('Firmware version is not match, Test failed !!')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Wi-Fi Enable Check Script ***
        Examples: ./run.sh bat_scripts_new/fw_update_pass_check.py --uut_ip 10.92.224.68 --version_check 5.0.0-119\
        """)

    # Test Arguments
    parser.add_argument('--version_check', help='firmware version to compare')

    test = FWUpdatePASSCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
