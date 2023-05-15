# -*- coding: utf-8 -*-
""" Check nasAdmin daemon.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class CheckNasAdminDaemon(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-5510 - Check nasAdmin Daemon'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5510'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        out, err = self.ssh_client.execute_cmd('ps | grep nasadmin | grep -v grep')
        if not out:
            raise self.err.TestFailure("nasAdmin daemon doesn't exist!!!")

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Check NasAdmin Daemon ***
        """)

    test = CheckNasAdminDaemon(parser)
    resp = test.main()
    print 'test result: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
