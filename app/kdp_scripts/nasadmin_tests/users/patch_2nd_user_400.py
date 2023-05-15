# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: PATCH /v2/user/{user-id} - 400 - 2nd user
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import json
import sys
import os
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import NasAdmin
from platform_libraries.test_utils import \
    read_lines_to_string, run_test_with_data, api_negative_test, run_test_with_suit, exec_filter
from kdp_scripts.test_utils.test_case_utils import \
    nsa_declare_2nd_user, nsa_after_test_user, nsa_add_argument_2nd_user, nsa_init_2nd_user


class Patch2ndUser400(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Update user - 2nd user - 400 status'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3365'

    def declare(self):
        self.exec_test = None
        nsa_declare_2nd_user(self)

    def test(self):
        nsa_init_2nd_user(self)
        token = self.nasadmin_2nd.login_with_cloud_token(cloud_token=self.rest_2nd.access_token)

        run_test_with_suit(
            test_suit=exec_filter(
                exec_list=[
                    # set owner info to default at end of test
                    (self.patch_2nd_user_400_test_with_dataset, {'user_id': token['userID']}),
                    (self.patch_with_forbidden_usernames_test_for_2nd_user, {'user_id': token['userID']}),
                    self.patch_with_improper_id_test_for_2nd_user
                ],
                filter_names=self.exec_test # for specifying sub-tests to execute
            )
        )

    def after_test(self):
        nsa_after_test_user(self)

    def patch_2nd_user_400_test_with_dataset(self, user_id):
        run_test_with_data(
            test_data=[
                (user_id, s) for s in \
                    read_lines_to_string(os.path.dirname(__file__) + '/../test_data/Patch2ndUser400.txt')],
            test_method=self.patch_2nd_user_400_test
        )

    def patch_2nd_user_400_test(self, data_tuple):
        user_id = data_tuple[0]
        payload_str = data_tuple[1]
        api_negative_test(
            test_method=self.nasadmin_2nd._update_user,
            data_dict={'user_id': user_id, 'data': payload_str},
            expect_status=400
        )

    def patch_with_forbidden_usernames_test_for_2nd_user(self, user_id):
        resp = self.nasadmin_2nd.get_validation_info()
        for name in resp['forbiddenUsernames']:
            api_negative_test(
                test_method=self.nasadmin_2nd.update_user,
                data_dict={'user_id': user_id, 'username': name},
                expect_status=400
            )

    def patch_with_improper_id_test_for_2nd_user(self):
        api_negative_test(
            test_method=self.nasadmin_2nd.update_user,
            data_dict={'user_id': NasAdmin.Test.IMPROPER_ID, 'localAccess': False},
            expect_status=400
        )


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Patch 2nd user test for 400 status ***
        """)
    parser.add_argument('-et', '--exec_test', nargs='+', \
                        help='method names to execute. e.g. -et t1 t2 t3', default=None)
    nsa_add_argument_2nd_user(parser)

    test = Patch2ndUser400(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
