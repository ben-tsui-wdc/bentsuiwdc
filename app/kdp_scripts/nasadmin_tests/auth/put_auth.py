# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: PUT /v2/auth - 200
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
# 3rd party
import jwt


class PutAuth(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Refresh user token'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3361'

    def test(self):
        tokens = self.nasadmin.login_with_cloud_token(self.uut_owner.access_token)
        tokens = self.nasadmin.refresh_token(tokens['refresh'])
        assert tokens['userID'], 'userID is empty'
        assert tokens['admin'], 'admin is not True'

        public_key = self.nasadmin.get_public_key()['publickey']
        self.log.info("Decoding access token with public key")
        content = jwt.decode(tokens['access'], public_key)
        self.log.debug('Content: ' + pformat(content))

        self.log.info("Verify the access token by making get user call")
        self.nasadmin.get_user(user_id=tokens['userID'])

        self.log.info("Verify the refresh token by refreshing tojen again")
        tokens = self.nasadmin.refresh_token(tokens['refresh'])
        assert tokens['userID'], 'userID is empty'
        assert tokens['admin'], 'admin is not True'

        public_key = self.nasadmin.get_public_key()['publickey']
        self.log.info("Decoding access token with public key")
        content = jwt.decode(tokens['access'], public_key)
        self.log.debug('Content: ' + pformat(content))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Get server public key test ***
        """)

    test = PutAuth(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
