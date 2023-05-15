# -*- coding: utf-8 -*-
""" Test cases to check afp service is launch.
    https://jira.wdmv.wdc.com/browse/KAM-13975
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class AvahiServiceCheck(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'KAM-13975 - Avahi Daemon Check'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-13975'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        model = self.uut.get('model')
        avahi_daemon = self.adb.executeShellCommand('ps | grep avahi')[0]
        check_list1 = ['avahi-daemon: running']
        if model in ['yoda', 'yodaplus']:
            if avahi_daemon:
                raise self.err.TestFailure('Avahi Service Check Failed, avahi service should not be launched on {} !!'.format(model))
        else:
            if not all(word in avahi_daemon for word in check_list1):
                raise self.err.TestFailure('Avahi Service Check Failed, avahi is not launch on device !!')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Avahi Service Check Script ***
        Examples: ./run.sh bat_scripts_new/afp_service_check.py --uut_ip 10.92.224.68\
        """)

    test = AvahiServiceCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
