# -*- coding: utf-8 -*-
""" Test case to check the NFS service
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class NFSServiceCheck(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'NFS Service Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1525'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def before_test(self):
        self.ssh_client.enable_nfs_service()

    def test(self):
        self.log.info("Checking the NFS daemon...")
        nfs_service = self.ssh_client.execute_cmd('ps aux | grep nfs | grep -v grep')[0]
        if '[nfsiod]' not in nfs_service:
            raise self.err.TestFailure('NFS Service Check Failed!')


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** NFS Service Check test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/nfs_service_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = NFSServiceCheck(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
