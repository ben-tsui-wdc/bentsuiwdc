# -*- coding: utf-8 -*-
""" Test cases to check samba service is launch.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class SambaServiceCheck(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-193 - Samba Enabled Check'
    TEST_JIRA_ID = 'KDP-193'

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        stdout, stderr = self.ssh_client.execute_cmd('ps aux | grep smbd | grep -v grep')
        if 'smbd -D' not in stdout:
            raise self.err.TestFailure('smbd is not launched on the device!')

        stdout, stderr = self.ssh_client.execute_cmd('ps aux | grep nmbd | grep -v grep')
        if 'nmbd -D' not in stdout:
            raise self.err.TestFailure('nmbd is not launched on the device!')

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Samba Service Check Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/samba_service_check.py --uut_ip 10.92.224.68\
        """)

    test = SambaServiceCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
