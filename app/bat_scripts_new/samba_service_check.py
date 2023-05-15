# -*- coding: utf-8 -*-
""" Test cases to check samba service is launch.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class SambaServiceCheck(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Samba Service Check'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-13970'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        model = self.adb.getModel()
        samba_daemon = self.adb.executeShellCommand('ps | grep smbd')[0]
        check_list1 = ['smbd']
        if model in ['yoda', 'yodaplus']:
            if samba_daemon:
                raise self.err.TestFailure('Samba Service Check Failed, smbd should not be launched in {} !!'.format(model))
        else:
            if not all(word in samba_daemon for word in check_list1):
                raise self.err.TestFailure('Samba Service Check Failed, smbd is not launch on device !!')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Samba Service Check Script ***
        Examples: ./run.sh bat_scripts_new/samba_service_check.py --uut_ip 10.92.224.68\
        """)

    test = SambaServiceCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
