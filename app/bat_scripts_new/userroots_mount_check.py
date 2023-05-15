# -*- coding: utf-8 -*-
""" Test cases to check userRoots is mount on device.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class UserRootsMountOnDevice(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Check userRoots Mount on Device'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-13978'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        userRoots_check = self.adb.executeShellCommand('df | grep userRoots')[0]
        userRoots_check_list = ['/diskVolume0/restsdk/userRoots']
        if not all(word in userRoots_check for word in userRoots_check_list):
            raise self.err.TestFailure('userRoots is not mounted, Test Failed !!')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Check userRoots Mount Script ***
        Examples: ./run.sh bat_scripts_new/userroots_mount_check.py --uut_ip 10.92.224.68\
        """)

    test = UserRootsMountOnDevice(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
