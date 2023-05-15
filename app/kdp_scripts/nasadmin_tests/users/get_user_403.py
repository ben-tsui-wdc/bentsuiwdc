# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: GET /v2/user/{user-id} - 403
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from kdp_scripts.test_utils.test_case_utils import \
    nsa_declare_2nd_user, nsa_after_test_user, nsa_add_argument_2nd_user, nsa_init_2nd_user
from platform_libraries.constants import NasAdmin
from platform_libraries.test_utils import api_negative_test, run_test_with_suit, exec_filter


class GetUser403(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Get specific user by ID - 403 status'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3376'

    def declare(self):
        nsa_declare_2nd_user(self)
        self.exec_test = None

    def test(self):
        run_test_with_suit(
            test_suit=exec_filter(
                exec_list=[
                    self.test_with_not_exist_id,
                    self.test_with_2nd_user_id
                ],
                filter_names=self.exec_test # for specifying sub-tests to execute
            )
        )

    def test_with_not_exist_id(self):
        self.log.info('Get user with not exist user ID')
        api_negative_test(
            test_method=self.nasadmin.get_user,
            data_dict={'user_id': NasAdmin.Test.NOT_EXIST_USER_ID},
            expect_status=403
        )

    def test_with_2nd_user_id(self):
        self.log.info('Get user by 2nd user ID with owner token')
        nsa_init_2nd_user(self)
        token = self.nasadmin_2nd.login_with_cloud_token(cloud_token=self.rest_2nd.access_token)

        api_negative_test(
            test_method=self.nasadmin.get_user,
            data_dict={'user_id': token['userID']},
            expect_status=403
        )

    def after_test(self):
        nsa_after_test_user(self)


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Get user test for 403 status ***
        """)
    nsa_add_argument_2nd_user(parser)
    parser.add_argument('-et', '--exec_test', nargs='+', \
                        help='method names to execute. e.g. -et t1 t2 t3', default=None)

    test = GetUser403(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
