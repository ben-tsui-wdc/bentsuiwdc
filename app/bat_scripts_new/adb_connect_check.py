# -*- coding: utf-8 -*-
""" Test cases to check adb connection.
    https://jira.wdmv.wdc.com/browse/KAM-13969
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class ADBConnectCheck(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'KAM-13969 - Network ADB connection test'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-13969'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.timeout = 60*30
        self.result = True

    def test(self):
        check = self.adb.executeShellCommand('cat /proc/version')[0]
        if 'Linux version' in check:
            self.result = True
        else:
            self.result = False

    def after_test(self):
        if not self.result:
            raise self.err.TestFailure('ADB Connection Check Failed !!')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Cloud Environment Check Script ***
        Examples: ./run.sh bat_scripts_new/adb_connect_check.py --uut_ip 10.92.224.68\
        """)

    test = ADBConnectCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
