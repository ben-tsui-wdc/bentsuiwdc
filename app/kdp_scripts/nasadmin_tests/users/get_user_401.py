# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: GET /v2/user/{user-id} - 401
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import NasAdmin
from platform_libraries.test_utils import api_negative_test


class GetUser401(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Get specific user by ID - 401 status'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3376'

    def test(self):
        api_negative_test(
            test_method=self.nasadmin.get_user,
            data_dict={'user_id': NasAdmin.Test.NOT_EXIST_ID},
            expect_status=401,
            pre_handler=self.nasadmin.hide_access_token,
            finally_handler=self.nasadmin.reveal_access_token
        )


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Get user test for 401 status ***
        """)

    test = GetUser401(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
