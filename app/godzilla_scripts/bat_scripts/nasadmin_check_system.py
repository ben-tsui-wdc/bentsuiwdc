# -*- coding: utf-8 -*-
""" Test case to check nasAdmin system status
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import json
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from platform_libraries.nasadmin_api import NasAdminAPI


class NasAdminCheckSystemStatus(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'NasAdmin Check System Status'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-5284'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def test(self):
        result = self.ssh_client.get_device_status()
        check_list = ['scanning', 'eula_status', 'restoring', 'booting']
        if all(status in result.keys() for status in check_list):
            self.log.info("Check nasAdmin system status successfully")
        else:
            raise self.err.TestFailure('Suppose to get all the status in {} but only get {}!'.
                                       format(check_list, result.keys()))


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Nas Admin Check System Status test on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/nasadmin_get_token.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = NasAdminCheckSystemStatus(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
