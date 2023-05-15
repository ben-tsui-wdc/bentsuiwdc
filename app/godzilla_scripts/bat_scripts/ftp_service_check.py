# -*- coding: utf-8 -*-
""" Test case to check the aqpp manager daemon
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class FTPServiceCheck(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'FTP Service Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1597'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def before_test(self):
        self.ssh_client.enable_ftp_service()

    def test(self):
        self.log.info("Checking the FTP daemon...")
        ftp_service = self.ssh_client.execute_cmd('ps aux | grep ftp | grep -v grep')[0]
        if 'pure-ftpd' not in ftp_service:
            raise self.err.TestFailure('FTP Service Check Failed!')


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** FTP Service Check test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/ftp_service_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = FTPServiceCheck(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
