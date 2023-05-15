# -*- coding: utf-8 -*-
""" Test case to check the app manager daemon
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import re
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class LoadAPPManager(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Load APP Manager Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'Disabled'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        self.log.info("Checking app manager daemon")
        app_manager = self.ssh_client.get_app_manager_service()
        if "/usr/sbin/wdappmgr" not in app_manager:
            raise self.err.TestFailure('Cannot find APP manager service!')


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Load APP Manager Check test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/load_app_manager.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = LoadAPPManager(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
