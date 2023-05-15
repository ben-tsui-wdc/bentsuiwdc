# -*- coding: utf-8 -*-
""" Test case to check afp service is not exist on device
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class AFPServiceDisableCheck(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-211 - Verify AFP Daemon is not exist'
    TEST_JIRA_ID = 'KDP-211'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        exitcode, _ = self.ssh_client.execute('pidof afpd')
        if exitcode == 0: raise self.err.TestFailure("afpd daemon is exist!")


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** AFP Daemon Disable Check Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/afp_service_disable_check.py --uut_ip 10.92.224.68\
        """)

    test = AFPServiceDisableCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
