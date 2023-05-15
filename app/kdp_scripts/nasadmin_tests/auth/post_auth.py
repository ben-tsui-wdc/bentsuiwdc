# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: POST /v3/auth - 200
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.assert_utls import nsa_assert_user_by_dict
from platform_libraries.test_utils import run_test_with_suit, exec_filter


class PostAuth(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Login user test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3409'

    def declare(self):
        self.exec_test = None
        self.owner_id = None
        self.username = 'owner'
        self.password = 'password'

    def test(self):
        run_test_with_suit(
            test_suit=exec_filter(
                exec_list=[
                    self.login_cloud_token_test,
                    self.login_local_password_test,
                    self.login_local_password_test_with_local_access_disabled
                ],
                filter_names=self.exec_test # for specifying sub-tests to execute
            )
        )

    def login_cloud_token_test(self):
        cloud_token = self.uut_owner.owner_access_token
        tokens = self.nasadmin.login_with_cloud_token(cloud_token)
        if not self.owner_id: # save it to other sub-tests
            self.owner_id = tokens['userID']
        self._verify_owner_token(tokens)
        self._verify_token_by_get_user_call(user_id=tokens['userID'])

    def _verify_owner_token(self, tokens):
        assert tokens['userID'], 'userID is empty'
        assert tokens['admin'], 'admin is not True'

    def _verify_token_by_get_user_call(self, user_id):
        self.log.info("Verify the access token by making get user call")
        self.nasadmin.get_user(user_id=user_id)

    def _get_owner_id(self):
        if not self.owner_id:
            cloud_token = self.uut_owner.owner_access_token
            self.owner_id = self.nasadmin.login_with_cloud_token(cloud_token)['userID']
        return self.owner_id

    def _reset_owner_info(self):
        try:
            self.log.info('Resetting owner info to default')
            self.nasadmin.update_user(self._get_owner_id(), localAccess=False, username="", password="")
            self.log.info('Logging again with cloud token to update access token in clients')
            tokens = self.nasadmin.login_with_cloud_token(self.uut_owner.owner_access_token)
        except Exception as e:
            self.log.info('Got an error: {}'.format(e))

    def login_local_password_test(self):
        owner_id = self._get_owner_id()
        try:
            self.log.info("Enabling local access to owner")
            resp = self.nasadmin.update_user(
                owner_id, localAccess=True, username=self.username, password=self.password)
            nsa_assert_user_by_dict(
                check_data_dict={'localAccess': True, 'username': self.username}, cmp_user=resp)

            self.log.info("Logging with local password")
            tokens = self.nasadmin.login_with_local_password(self.username, self.password)
            self._verify_owner_token(tokens)
            self._verify_token_by_get_user_call(user_id=owner_id)
        finally:
            self._reset_owner_info()

    def login_local_password_test_with_local_access_disabled(self):
        owner_id = self._get_owner_id()
        try:
            self.log.info("Enabling local access to owner")
            resp = self.nasadmin.update_user(
                owner_id, localAccess=False, username=self.username, password=self.password)
            nsa_assert_user_by_dict(
                check_data_dict={'localAccess': False, 'username': self.username}, cmp_user=resp)

            self.log.info("Logging with local password")
            tokens = self.nasadmin.login_with_local_password(self.username, self.password)
            self._verify_owner_token(tokens)
            self._verify_token_by_get_user_call(owner_id)
        finally:
            self._reset_owner_info()


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Login user test ***
        """)
    parser.add_argument('-et', '--exec_test', nargs='+', \
                        help='method names to execute. e.g. -et t1 t2 t3', default=None)

    test = PostAuth(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
