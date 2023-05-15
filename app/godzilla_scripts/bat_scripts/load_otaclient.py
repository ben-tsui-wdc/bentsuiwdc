# -*- coding: utf-8 -*-
""" Test case to check the otaclient service
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import re
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class LoadOTAClient(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Load OTA Client Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1507'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False,
        'enable_auto_ota': True
    }

    def test(self):
        self.log.info("Checking RestSDK module")
        ota_client = self.ssh_client.get_otaclient_service()
        if not ota_client:
            raise self.err.TestFailure('Cannot find OTA client service!')


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Load OTA Client Check test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/load_otaclient.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = LoadOTAClient(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
