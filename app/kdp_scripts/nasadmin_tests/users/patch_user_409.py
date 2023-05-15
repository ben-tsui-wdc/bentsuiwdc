# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: PATCH /v2/user/{user-id} - 409 - Owner user
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
from platform_libraries.test_utils import api_negative_test, run_test_with_suit, exec_filter
from kdp_scripts.test_utils.test_case_utils import \
    nsa_declare_2nd_user, nsa_after_test_user, nsa_add_argument_2nd_user, nsa_init_2nd_user


class PatchUser409(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Update user - Owner user - 409 status'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3365'

    def declare(self):
        self.exec_test = None
        nsa_declare_2nd_user(self)

    def test(self):
        owner_token = self.nasadmin.login_owner()
        nsa_init_2nd_user(self)
        user_2nd_token = self.nasadmin_2nd.login_with_cloud_token(cloud_token=self.rest_2nd.access_token)

        run_test_with_suit(
            test_suit=exec_filter(
                exec_list=[
                    (
                        self.patch_user_409_test_duplicate_user_name,
                        {'owner_id': owner_token['userID'], 'user_2nd_id': user_2nd_token['userID']}
                    ),
                    (
                        self.patch_user_409_test_duplicate_space_name,
                        {'owner_id': owner_token['userID'], 'user_2nd_id': user_2nd_token['userID']}
                    ),
                    (
                        self.patch_user_409_test_enable_with_duplicate_default_space_name,
                        {'owner_id': owner_token['userID'], 'user_2nd_id': user_2nd_token['userID']}
                    ),
                    (
                        self.patch_user_409_test_with_system_space_name,
                        {'owner_id': owner_token['userID']}
                    )
                ],
                filter_names=self.exec_test # for specifying sub-tests to execute
            )
        )

    def after_test(self):
        nsa_after_test_user(self)

    def patch_user_409_test_duplicate_user_name(self, owner_id, user_2nd_id):
        try:
            self.log.info('Setting owner username')
            self.nasadmin.update_user(owner_id, username="owner")
            self.log.info('Trying to set 2nd user username to conflict')
            api_negative_test(
                test_method=self.nasadmin_2nd.update_user,
                data_dict={'user_id': user_2nd_id, 'username': 'owner'},
                expect_status=409
            )
            api_negative_test(
                test_method=self.nasadmin_2nd.update_user,
                data_dict={'user_id': user_2nd_id, 'username': 'Owner'},
                expect_status=409
            )
            api_negative_test(
                test_method=self.nasadmin_2nd.update_user,
                data_dict={'user_id': user_2nd_id, 'username': 'owneR'},
                expect_status=409
            )
            api_negative_test(
                test_method=self.nasadmin_2nd.update_user,
                data_dict={'user_id': user_2nd_id, 'username': 'OWNER'},
                expect_status=409
            )
        finally:
            self.log.info('Recovering users information')
            self.nasadmin.update_user(owner_id, username="")
            self.nasadmin_2nd.update_user(user_2nd_id, username="")

    def patch_user_409_test_duplicate_space_name(self, owner_id, user_2nd_id):
        try:
            self.log.info('Setting owner space name')
            owner_cloud_user = self.uut_owner.get_cloud_user()
            space_name = owner_cloud_user['user_metadata']['first_name']
            self.nasadmin.update_user(
                owner_id, localAccess=True, username=self.nasadmin.local_name, password=self.nasadmin.local_password,
                spaceName=space_name
            )
            self.log.info('Trying to set 2nd user space name to conflict')
            api_negative_test(
                test_method=self.nasadmin_2nd.update_user,
                data_dict={
                    'user_id': user_2nd_id, 'localAccess': True, 'username': self.nasadmin_2nd.local_name,
                    'password': self.nasadmin_2nd.local_password, 'spaceName': space_name},
                expect_status=409
            )
        finally:
            self.log.info('Recovering users information')
            self.nasadmin.update_user(owner_id, localAccess=False, username="", password="")
            cloud_user_2nd = self.rest_2nd.get_cloud_user()
            space_name = cloud_user_2nd['user_metadata']['first_name']
            self.nasadmin_2nd.update_user(
                user_2nd_id, localAccess=False, username="", password="", spaceName=space_name)

    def patch_user_409_test_enable_with_duplicate_default_space_name(self, owner_id, user_2nd_id):
        try:
            self.log.info('Enabling local access to owner user')
            self.nasadmin.update_user(
                owner_id, localAccess=True, username=self.nasadmin.local_name, password=self.nasadmin.local_password
            )
            self.log.info('Trying to enable local access to 2nd user to conflict')
            api_negative_test(
                test_method=self.nasadmin_2nd.update_user,
                data_dict={
                    'user_id': user_2nd_id, 'localAccess': True, 'username': self.nasadmin_2nd.local_name,
                    'password': self.nasadmin_2nd.local_password},
                expect_status=409
            )
        finally:
            self.log.info('Recovering users information')
            self.nasadmin.update_user(owner_id, localAccess=False, username="", password="")
            self.nasadmin_2nd.update_user(user_2nd_id, localAccess=False, username="", password="")

    def patch_user_409_test_with_system_space_name(self, owner_id):
        try:
            self.log.info('Trying to set user space name to "public"')
            api_negative_test(
                test_method=self.nasadmin.update_user,
                data_dict={
                    'user_id': owner_id, 'localAccess': True, 'username': self.nasadmin.local_name,
                    'password': self.nasadmin.local_password, 'spaceName': 'public'
                },
                expect_status=409
            )
            model = self.uut.get('model')
            if 'monarch' in model or 'pelican' in model:
                api_negative_test(
                    test_method=self.nasadmin.update_user,
                    data_dict={
                        'user_id': owner_id, 'localAccess': True, 'username': self.nasadmin.local_name,
                        'password': self.nasadmin.local_password, 'spaceName': 'TimeMachineBackup'
                    },
                    expect_status=409
                )
        finally:
            self.log.info('Recovering users information')
            owner_cloud_user = self.uut_owner.get_cloud_user()
            space_name = owner_cloud_user['user_metadata']['first_name']
            self.nasadmin.update_user(owner_id, localAccess=False, username="", password="", spaceName=space_name)


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Patch user test for 409 status ***
        """)
    parser.add_argument('-et', '--exec_test', nargs='+', \
                        help='method names to execute. e.g. -et t1 t2 t3', default=None)
    nsa_add_argument_2nd_user(parser)

    test = PatchUser409(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
