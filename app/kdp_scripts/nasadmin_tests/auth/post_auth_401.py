# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: POST /v3/auth - 401 status
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


class PostAuth401(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Login user test - 401 status'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3381'

    def declare(self):
        self.exec_test = None

    def test(self):
        cloud_token = self.uut_owner.owner_access_token
        self.nasadmin.login_with_cloud_token(cloud_token)
        run_test_with_suit(
            test_suit=exec_filter(
                exec_list=[
                    self.login_with_wrong_username_test,
                    self.login_with_wrong_password_test,
                    self.login_with_bad_cloud_token_test
                ],
                filter_names=self.exec_test # for specifying sub-tests to execute
            )
        )

    def login_with_wrong_username_test(self):
        api_negative_test(
            test_method=self.nasadmin.login_with_local_password,
            data_dict={'username': 'WrongName', 'password': self.nasadmin.local_password},
            expect_status=401,
            pre_handler=self.nasadmin.enable_local_access,
            finally_handler=self.nasadmin.disable_local_access
        )

    def login_with_wrong_password_test(self):
        api_negative_test(
            test_method=self.nasadmin.login_with_local_password,
            data_dict={'username': self.nasadmin.local_name, 'password': 'WrongPassword'},
            expect_status=401,
            pre_handler=self.nasadmin.enable_local_access,
            finally_handler=self.nasadmin.disable_local_access
        )

    def login_with_bad_cloud_token_test(self):
        api_negative_test(
            test_method=self.nasadmin.login_with_cloud_token,
            data_dict={'cloud_token': 'BadCloudToken'},
            expect_status=401
        )


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Login user test for 401 status ***
        """)
    parser.add_argument('-et', '--exec_test', nargs='+', \
                        help='method names to execute. e.g. -et t1 t2 t3', default=None)

    test = PostAuth401(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
