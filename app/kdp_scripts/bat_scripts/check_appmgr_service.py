# -*- coding: utf-8 -*-
""" Check app manager service is launch on the device
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class CheckAppManagerService(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-442 - App Manager Daemon Check'
    TEST_JIRA_ID = 'KDP-442,KDP-1935,KDP-1936'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        exitcode, _ = self.ssh_client.execute('pidof kdpappmgr')
        if exitcode != 0: raise self.err.TestFailure("kdpappmgr process not found")
        exitcode, _ = self.ssh_client.execute('pidof kdpappmgrd')
        if exitcode != 0: raise self.err.TestFailure("kdpappmgrd process not found")

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Check App Manager Service Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/check_appmgr_service.py --uut_ip 10.92.224.68\
        """)

    test = CheckAppManagerService(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
