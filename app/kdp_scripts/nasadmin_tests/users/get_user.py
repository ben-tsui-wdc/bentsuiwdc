# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: GET /v2/user/{user-id} - 200 - Owner user
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.assert_utls import nsa_assert_user


class GetUser(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Get specific user by ID - Owner user'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3414'

    def test(self):
        owner_cloud_user = self.uut_owner.get_cloud_user()
        token = self.nasadmin.login_owner()
        owner = self.nasadmin.get_user(token['userID'])
        nsa_assert_user(owner_cloud_user, cmp_user=owner, localAccess=False, username="", description="")


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Get user test ***
        """)

    test = GetUser(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
