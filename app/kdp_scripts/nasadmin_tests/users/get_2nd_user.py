# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: GET /v2/user/{user-id} - 200 - 2nd user
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from kdp_scripts.test_utils.test_case_utils import \
    nsa_declare_2nd_user, nsa_after_test_user, nsa_add_argument_2nd_user, nsa_init_2nd_user
from platform_libraries.assert_utls import nsa_assert_user


class Get2ndUser(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Get specific user by ID - 2nd user'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3414'

    def declare(self):
        nsa_declare_2nd_user(self)

    def test(self):
        nsa_init_2nd_user(self)
        cloud_user_2nd = self.rest_2nd.get_cloud_user()
        token = self.nasadmin_2nd.login_with_cloud_token(cloud_token=self.rest_2nd.access_token)
        user_2nd = self.nasadmin_2nd.get_user(token['userID'])
        nsa_assert_user(cloud_user_2nd, cmp_user=user_2nd, localAccess=False, username="", description="")

    def after_test(self):
        nsa_after_test_user(self)


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Get user test for 2nd user ***
        """)
    nsa_add_argument_2nd_user(parser)

    test = Get2ndUser(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
