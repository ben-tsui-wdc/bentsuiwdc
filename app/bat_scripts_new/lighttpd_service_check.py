# -*- coding: utf-8 -*-
""" Test cases to check light web server service(lighttpd) is launch.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class LighttpdServiceCheck(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Light Web Server Service Check'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-24575'
    COMPONENT = 'PLATFORM'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        lighttpd_service = self.adb.executeShellCommand('ps | grep lighttpd')[0]
        check_list1 = ['lighttpd']
        if not all(word in lighttpd_service for word in check_list1):
            raise self.err.TestFailure('Lighttpd service check Failed !!')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Lighttpd Service Check Script ***
        Examples: ./run.sh bat_scripts_new/lighttpd_service_check.py --uut_ip 10.92.224.68\
        """)

    test = LighttpdServiceCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
