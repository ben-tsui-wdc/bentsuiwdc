# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: PATCH /v2/user/{user-id} - 400 - Owner user
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


class PatchUser400(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Update user - Owner user - 400 status'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3365'

    def declare(self):
        self.exec_test = None

    def test(self):
        token = self.nasadmin.login_owner()
        run_test_with_suit(
            test_suit=exec_filter(
                exec_list=[
                    # set owner info to default at end of test
                    (self.patch_user_400_test_with_dataset, {'user_id': token['userID']}),
                    (self.patch_with_forbidden_usernames_test, {'user_id': token['userID']}),
                    self.patch_with_improper_id_test
                ],
                filter_names=self.exec_test # for specifying sub-tests to execute
            )
        )

    def patch_user_400_test_with_dataset(self, user_id):
        run_test_with_data(
            test_data=[
                (user_id, s) for s in \
                    read_lines_to_string(os.path.dirname(__file__) + '/../test_data/PatchUser400.txt')],
            test_method=self.patch_user_400_test
        )

    def patch_user_400_test(self, data_tuple):
        user_id = data_tuple[0]
        payload_str = data_tuple[1]
        api_negative_test(
            test_method=self.nasadmin._update_user,
            data_dict={'user_id': user_id, 'data': payload_str},
            expect_status=400
        )

    def patch_with_forbidden_usernames_test(self, user_id):
        resp = self.nasadmin.get_validation_info()
        for name in resp['forbiddenUsernames']:
            api_negative_test(
                test_method=self.nasadmin.update_user,
                data_dict={'user_id': user_id, 'username': name},
                expect_status=400
            )

    def patch_with_improper_id_test(self):
        api_negative_test(
            test_method=self.nasadmin.update_user,
            data_dict={'user_id': NasAdmin.Test.IMPROPER_ID, 'localAccess': False},
            expect_status=400
        )


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Patch user test for 400 status ***
        """)
    parser.add_argument('-et', '--exec_test', nargs='+', \
                        help='method names to execute. e.g. -et t1 t2 t3', default=None)

    test = PatchUser400(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
