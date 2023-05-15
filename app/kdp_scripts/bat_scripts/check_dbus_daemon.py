# -*- coding: utf-8 -*-
""" Check D-bus daemon is launced on the device
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class CheckDbusDaemon(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-1015 - Check D-Bus daemon'
    TEST_JIRA_ID = 'KDP-1015'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        exitcode, _ = self.ssh_client.execute('pidof dbus-daemon')
        if exitcode != 0: raise self.err.TestFailure("dbus-daemon process not found")

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Check dbus daemon Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/check_dbus_daemon.py --uut_ip 10.92.224.68\
        """)

    test = CheckDbusDaemon(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
