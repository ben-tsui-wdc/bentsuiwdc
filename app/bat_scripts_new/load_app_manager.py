# -*- coding: utf-8 -*-
""" Test cases to check appmgr service is loaded.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class LoadAPPManager(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Load APP Manager Check'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-13974'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.result = True

    def test(self):
        app_daemon = self.adb.executeShellCommand('ps | grep appmgr | grep -v grep')[0]
        app_check_list1 = ['appmgr']
        if all(word in app_daemon for word in app_check_list1):
            self.result = True
        else:
            self.result = False

    def after_test(self):
        if not self.result:
            raise self.err.TestFailure('Load APP Manager check Failed !!')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Load APP Manager Check Script ***
        Examples: ./run.sh bat_scripts_new/load_app_manager.py --uut_ip 10.92.224.68\
        """)

    test = LoadAPPManager(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
