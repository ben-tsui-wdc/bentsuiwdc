# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: GET /v2/auth/public-key - 200
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


class GetPublicKey(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Get server public key'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3364'

    def test(self):
        tokens = self.nasadmin.login_with_cloud_token(self.uut_owner.access_token)
        public_key = self.nasadmin.get_public_key()['publickey']
        self.log.info("Decoding access token with public key")
        content = jwt.decode(tokens['access'], public_key)
        self.log.debug('Content: ' + pformat(content))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Get server public key test ***
        """)

    test = GetPublicKey(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
