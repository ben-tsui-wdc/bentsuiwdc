# -*- coding: utf-8 -*-
""" Test for API: GET /v1/users/id (KAM-19232).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class GetOwnerInfoByIDTest(TestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Get Owner Info By ID'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-19232'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def test(self):
        owner_info = self.uut_owner.get_user(user_id=self.uut_owner.get_user_id())
        self.log.info('API Response: \n{}'.format(pformat(owner_info)))
        # Test passed if it response HTTP status code 200


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** GetOwnerInfoByIDTest test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/get_owner_info_by_id.py --uut_ip 10.136.137.159\
        """)

    test = GetOwnerInfoByIDTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
