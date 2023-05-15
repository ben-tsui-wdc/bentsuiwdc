# -*- coding: utf-8 -*-
""" Test cases to check otaclient service is loaded.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class LoadOTAClient(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Load OTA Client Check'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-13977'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.result = True

    def test(self):
        otaclient_daemon = self.adb.executeShellCommand('ps | grep otaclient')[0]
        check_list1 = ['otaclient']
        if all(word in otaclient_daemon for word in check_list1):
            self.result = True
        else:
            self.result = False

    def after_test(self):
        if not self.result:
            raise self.err.TestFailure('Load OTA Client check Failed !!')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Load OTA Client Check Script ***
        Examples: ./run.sh bat_scripts_new/load_otaclient.py --uut_ip 10.92.224.68\
        """)

    test = LoadOTAClient(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
