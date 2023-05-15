# -*- coding: utf-8 -*-
""" Test case to check the userRoots is mounted on test device
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import re
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class UserRootsMountOnDevice(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Check userRoots Mount on Device'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1110'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': True
    }

    def test(self):
        self.log.info("Checking userRoots mount")
        user_roots = self.ssh_client.get_user_roots_path()
        if not user_roots:
            raise self.err.TestFailure('The userRoots is not mounted!')


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Check userRoots Mount on Device test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/user_roots_mount_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = UserRootsMountOnDevice(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
