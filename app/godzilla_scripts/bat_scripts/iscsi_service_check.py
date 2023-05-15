# -*- coding: utf-8 -*-
""" Test case to check the iSCSI service
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class iSCSIServiceCheck(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'iSCSI Service Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1451'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        stdout, stderr = self.ssh_client.execute_cmd('ps aux | grep iscsi | grep -v grep')
        if '[iscsi_eh]' not in stdout:
            raise self.err.TestFailure('iSCSI Service Check Failed!')


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** iSCSI Service Check test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/iscsi_service_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = iSCSIServiceCheck(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
