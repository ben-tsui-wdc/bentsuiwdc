# -*- coding: utf-8 -*-
""" Test cases to check avahi service is launch.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class AvahiServiceCheck(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-198 - Avahi Daemon Check'
    # Popcorn
    TEST_JIRA_ID = 'KDP-198'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        avahi_daemon = self.ssh_client.execute('ps aux | grep avahi | grep -v grep')[1]
        check_list = ['avahi-daemon: running']
        if not all(word in avahi_daemon for word in check_list):
            raise self.err.TestFailure('Avahi Service Check Failed, avahi is not launch on the device !!')

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Avahi Service Check Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/avahi_service_check.py --uut_ip 10.200.141.103\
        """)

    test = AvahiServiceCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
