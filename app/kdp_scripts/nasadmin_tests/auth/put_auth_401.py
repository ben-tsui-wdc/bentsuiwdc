# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: PUT /v2/auth - 401 status
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import NasAdmin
from platform_libraries.test_utils import \
    api_negative_test, run_test_with_suit, exec_filter


class PutAuth401(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Refresh user token - 401 status'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3403'

    def declare(self):
        self.exec_test = None

    def test(self):
        cloud_token = self.uut_owner.owner_access_token
        self.nasadmin.login_with_cloud_token(cloud_token)
        run_test_with_suit(
            test_suit=exec_filter(
                exec_list=[
                    self.refresh_token_with_bad_user_token_test,
                    self.refresh_token_with_bad_refresh_token_test,
                ],
                filter_names=self.exec_test  # for specifying sub-tests to execute
            )
        )

    def refresh_token_with_bad_user_token_test(self):
        api_negative_test(
            test_method=self.nasadmin.refresh_token,
            data_dict={},
            expect_status=401,
            pre_handler=self.nasadmin.hide_access_token,
            finally_handler=self.nasadmin.reveal_access_token
        )

    def refresh_token_with_bad_refresh_token_test(self):
        api_negative_test(
            test_method=self.nasadmin.refresh_token,
            data_dict={'refresh_token': 'BadRefreshToken'},
            expect_status=401
        )


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Refresh user token for 401 status ***
        """)
    parser.add_argument('-et', '--exec_test', nargs='+', \
                        help='method names to execute. e.g. -et t1 t2 t3', default=None)

    test = PutAuth401(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
