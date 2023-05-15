# -*- coding: utf-8 -*-
""" Test case to check default share folders
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class CheckShareDefaultList(GodzillaTestCase):

    TEST_SUITE = 'Godzilla Sanity'
    TEST_NAME = 'Default Share List Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1169'
    PRIORITY = 'Blocker'
    COMPONENT = 'Platform'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.default_list = ['Public', 'TimeMachineBackup']

    def test(self):
        share_permissions = self.ssh_client.get_share_permission()
        for folder in self.default_list:
            if folder in share_permissions.keys():
                self.log.info("Found folder: {} in the default share list".format(folder))
            else:
                raise self.err.TestFailure("Cannot find the default folder: {}".format(folder))


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Default Share List Check test on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/function_tests/default_share_list_check.py \
        --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = CheckShareDefaultList(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
