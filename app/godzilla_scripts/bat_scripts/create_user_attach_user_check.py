# -*- coding: utf-8 -*-
""" Test case to create and attach user to the test device
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class CreateUserAttachUser(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Create User & Attach User Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1081'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': True
    }

    def test(self):
        self.uut_owner.wait_until_cloud_connected(60)
        users, next_page_token = self.uut_owner.get_users(limit=1000)
        self.log.info('API Response: \n{}'.format(pformat(users)))
        self.verify_result(users)

    def verify_result(self, users):
        owner_id = self.uut_owner.get_user_id()
        for user in users:
            if user['id'] == owner_id:
                self.log.info('Check owner in list: PASSED')
                return
        self.log.error('Check owner in list: FAILED')
        raise self.err.TestFailure('Check owner in list failed!')


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Create User & Attach User Check test for Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/create_user_attach_user_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)

    test = CreateUserAttachUser(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
