# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: GET /v2/user/{user-id} - 400
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import NasAdmin
from platform_libraries.test_utils import api_negative_test


class GetUser400(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Get specific user by ID - 400 status'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3376'

    def test(self):
        api_negative_test(
            test_method=self.nasadmin.get_user,
            data_dict={'user_id': NasAdmin.Test.IMPROPER_ID},
            expect_status=400
        )


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Get user test for 400 status ***
        """)

    test = GetUser400(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
