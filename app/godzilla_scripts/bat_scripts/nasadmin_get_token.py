# -*- coding: utf-8 -*-
""" Test case to get nasAdmin token
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from platform_libraries.nasadmin_api import NasAdminAPI


class NasAdminGetToken(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'NasAdmin Get Token'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-5283'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.nasAdmin = NasAdminAPI(uut_ip=self.env.ssh_ip)

    def test(self):
        result = self.nasAdmin.get_token()
        if not result:
            raise self.err.TestFailure('Failed to get nasAdmin token!')
        else:
            self.log.info('Get nasAdmin token successfully.')


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Nas Admin Get Token test on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/nasadmin_get_token.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = NasAdminGetToken(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
