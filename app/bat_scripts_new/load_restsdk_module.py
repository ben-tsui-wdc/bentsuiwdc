# -*- coding: utf-8 -*-
""" Test cases to check restsdk service is loaded.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class LoadRestsdkmodule(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Load Rest-SDK Module'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-13968'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.result = True

    def test(self):
        restsdk_daemon = self.adb.executeShellCommand('ps | grep restsdk')[0]
        restsdk_ls_list = self.adb.executeShellCommand('ls -l /data/wd/diskVolume0/restsdk/data/db')[0]
        check_list1 = ['restsdk-server']
        check_list2 = ['index.db', 'index.db-shm', 'index.db-wal']
        if all(word in restsdk_daemon for word in check_list1) and all(word in restsdk_ls_list for word in check_list2):
            self.result = True
        else:
            self.result = False

    def after_test(self):
        if not self.result:
            raise self.err.TestFailure('Load REST-SDK Module check Failed !!')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Load REST-SDK Module Check Script ***
        Examples: ./run.sh bat_scripts_new/load_restsdk_module.py --uut_ip 10.92.224.68\
        """)

    test = LoadRestsdkmodule(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
