# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: PATCH /v2/user/{user-id} - 415 status
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.test_utils import api_negative_test


class PatchUser415(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Update user - 415 status'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3365'

    def test(self):
        token = self.nasadmin.login_owner()
        api_negative_test(
            test_method=self.nasadmin._update_user,
            data_dict={
                'user_id': token['userID'],
                'data': '{"localAccess": false}',
                'headers': {'Content-Type': 'application/xml'}
            },
            expect_status=415
        )


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Patch user test for 415 status ***
        """)

    test = PatchUser415(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
