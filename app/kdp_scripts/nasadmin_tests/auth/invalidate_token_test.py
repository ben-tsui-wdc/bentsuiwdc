# -*- coding: utf-8 -*-
""" Invalidate nasAdmin token test
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from kdp_scripts.test_utils.test_case_utils import \
    nsa_add_argument_2nd_user, nsa_declare_2nd_user, nsa_after_test_user, nsa_init_2nd_user
from platform_libraries.test_utils import api_negative_test


class InvalidateTokenTest(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-5848 - invalidate nasAdmin token test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5848'

    def declare(self):
        nsa_declare_2nd_user(self)
        self.default_token = None
        self.new_password = 'newPassword'

    def test(self):
        nsa_init_2nd_user(self)
        self.default_token = self.nasadmin_2nd.login_with_cloud_token(cloud_token=self.rest_2nd.access_token)
        self.nasadmin_2nd.update_user(
            self.default_token['userID'], localAccess=True, username=self.local_username_2nd,
            password=self.local_password_2nd)
        self.detach_2nd_user = True

        self.log.info('*** Test for changing local password ***')
        test_tokens = self.get_test_tokens()
        self.verify_test_tokens_works(test_tokens)
        self.log.info('Changing password...')
        self.nasadmin_2nd.update_user(
            self.default_token['userID'], password=self.new_password)
        self.log.info('Verifying test tokens after changed local password...')
        self.verify_token(test_tokens, expected_codes={
            'by_cloud': 200,
            'by_refresh_cloud': 200,
            'by_local_pw': 401,
            'by_refresh_local_pw': 401
        })

        self.log.info('*** Test for detaching user ***')
        self.nasadmin_2nd.update_user(
            self.default_token['userID'], localAccess=True, username=self.local_username_2nd,
            password=self.local_password_2nd)
        test_tokens = self.get_test_tokens()
        self.verify_test_tokens_works(test_tokens)
        self.log.info('Detaching 2nd user from device...')
        nsa_after_test_user(self, wait_for_user_detached=True)
        self.detach_2nd_user = False
        self.verify_token(test_tokens, expected_codes={
            'by_cloud': 401,
            'by_refresh_cloud': 401,
            'by_local_pw': 401,
            'by_refresh_local_pw': 401
        })

    def get_test_tokens(self):
        self.log.info('Collecting tokens by cloud...')
        test_cloud_token = self.nasadmin_2nd.login_with_cloud_token(cloud_token=self.rest_2nd.access_token)
        time.sleep(5)
        test_refresh_token_by_cloud = self.nasadmin_2nd.refresh_token(refresh_token=test_cloud_token['refresh'])

        self.log.info('Collecting tokens by local...')
        test_local_token = self.nasadmin_2nd.login_with_local_password(
            username=self.local_username_2nd, password=self.local_password_2nd)
        time.sleep(5)
        test_refresh_token_by_local = self.nasadmin_2nd.refresh_token(refresh_token=test_local_token['refresh'])
        return {
            'by_cloud': test_cloud_token,
            'by_refresh_cloud': test_refresh_token_by_cloud,
            'by_local_pw': test_local_token,
            'by_refresh_local_pw': test_refresh_token_by_local
        }

    def verify_test_tokens_works(self, test_tokens):
        self.log.info('Make sure all of test tokens are good...')
        for name, token in test_tokens.iteritems():
            self.log.info('Checking token for {}...'.format(name))
            self.log.info('Token: {}'.format(token['access']))
            self.nasadmin_2nd._user_access_token = token['access']
            self.nasadmin_2nd.get_user(user_id=self.default_token['userID'])
        self.nasadmin_2nd._user_access_token = self.default_token['access']

    def verify_token(self, test_tokens, expected_codes):
        for name, token in test_tokens.iteritems():
            self.log.info('Checking token for {}...'.format(name))
            self.log.info('Token: {}'.format(token['access']))
            self.nasadmin_2nd._user_access_token = token['access']
            if expected_codes.get(name) == 200:
                self.nasadmin_2nd.get_user(user_id=self.default_token['userID'])
            else:
                api_negative_test(
                    test_method=self.nasadmin_2nd.get_user,
                    data_dict={'user_id': self.default_token['userID']},
                    expect_status=expected_codes.get(name)
                )

    def after_test(self):
        nsa_after_test_user(self)


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Invalidate nasAdmin token test ***
        """)
    nsa_add_argument_2nd_user(parser)

    test = InvalidateTokenTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
