# -*- coding: utf-8 -*-
""" Test for API: GET /v1/users (KAM-19231).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class GetUsersTest(TestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Get Users'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-19231'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def test(self):
        users, next_page_token = self.uut_owner.get_users(limit=1000)
        self.log.info('API Response: \n{}'.format(pformat(users)))
        self.verify_result(users)

    def verify_result(self, users):
        # Check owner in list
        owner_id = self.uut_owner.get_user_id()
        for user in users:
            if user['id'] == owner_id:
                self.log.info('Check owner in list: PASSED')
                return
        self.log.error('Check owner in list: FAILED')
        raise  self.err.TestFailure('Check owner in list failed.')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Get_Users test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/get_users.py --uut_ip 10.136.137.159\
        """)

    test = GetUsersTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
