# -*- coding: utf-8 -*-
""" Owner access tests.
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
from pprint import pformat
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
# 3rd party modules
import jwt
import requests


class NasAdminOwnerAccess(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-5512 - nasAdmin - Owner Access Test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5512'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.lite_mode = False
        self.need_reset_owner = False

    def test(self):
        cloud_token = self.uut_owner.owner_access_token

        self.log.info("Logging with cloud token")
        tokens = self.nasadmin.login_with_cloud_token(cloud_token)
        assert tokens['userID'], 'userID is empty'
        assert tokens['admin'], 'admin is not true'

        public_key = self.nasadmin.get_public_key()['publickey']

        self.log.info("Decoding access token with public key")
        content = jwt.decode(tokens['access'], public_key)
        self.log.debug('Content: ' + pformat(content))

        tokens = self.nasadmin.refresh_token(tokens['refresh'])
        assert tokens['userID'], 'userID is empty'

        self.log.info("Decoding the new access token with public key")
        content = jwt.decode(tokens['access'], public_key)
        self.log.debug('Content: ' + pformat(content))

        if self.lite_mode:
            owner = self.nasadmin.get_user(tokens['userID'])
        else:
            owner = self.nasadmin.get_owner()

        try:
            self.log.info("Getting owner info with bad token")
            self.nasadmin.hide_access_token()
            if self.lite_mode:
                self.nasadmin.get_user(tokens['userID'])
            else:
                self.nasadmin.get_owner()
        except requests.HTTPError as e:
            if e.response.status_code != 401:
                raise self.err.TestFailure('Status code is not 401, response: {}'.format(e))
        finally:
            self.nasadmin.reveal_access_token()

        self.need_reset_owner = True
        username = 'owner'
        password = 'password'
        self.log.info("Enabling local access to owner")
        resp = self.nasadmin.update_user(owner['id'], localAccess=True, username=username, password=password)
        assert resp['localAccess'], "localAccess is not true"
        assert resp['username'] == username, "username != " + username

        self.log.info("Logging with local password")
        tokens = self.nasadmin.login_with_local_password(username, password)
        assert tokens['userID'], 'userID is empty'
        assert tokens['admin'], 'admin is not true'

        self.log.info("Decoding the new access token with public key")
        content = jwt.decode(tokens['access'], public_key)
        self.log.debug('Content: ' + pformat(content))

        tokens = self.nasadmin.refresh_token(tokens['refresh'])

        self.log.info("Decoding the new access token with public key")
        content = jwt.decode(tokens['access'], public_key)
        self.log.debug('Content: ' + pformat(content))

        self.log.info("Disabling local access to owner")
        resp = self.nasadmin.update_user(owner['id'], localAccess=False)
        assert not resp['localAccess'], "localAccess is not false"

        self.log.info("Logging with local password")
        tokens = self.nasadmin.login_with_local_password(username, password)

        self.log.info("Removing username and password from owner")
        resp = self.nasadmin.update_user(owner['id'], username="", password="")
        assert not resp['localAccess'], "localAccess is not false"
        assert not resp['username'], "username is not set to empty"
        self.need_reset_owner = False

        try:
            self.log.info("Logging with local password again")
            self.nasadmin.login_with_local_password(username, password)
        except requests.HTTPError as e:
            if e.response.status_code != 401:
                raise self.err.TestFailure('Status code is not 401, response: {}'.format(e))
            self.log.info("Got 401 error as expected")

    def after_test(self):
        if self.need_reset_owner:
            try:
                self.log.info("Resetting owner to default value")
                if self.lite_mode:
                    cloud_token = self.uut_owner.owner_access_token
                    tokens = self.nasadmin.login_with_cloud_token(cloud_token)
                    owner = self.nasadmin.get_user(tokens['userID'])
                else:
                    owner = self.nasadmin.get_owner()
                resp = self.nasadmin.update_user(owner['id'], localAccess=False, username="", password="")
                assert not resp['localAccess'], "localAccess is not false"
                assert not resp['username'], "username is not set to empty"
            except Exception as e:
                self.log.error("Got an error on resetting: {}".format(e))


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** nasAdmin - Owner Access Test ***
        """)
    parser.add_argument('-lite', '--lite_mode', help='Execute for lite mode', action='store_true')

    test = NasAdminOwnerAccess(parser)
    resp = test.main()
    print 'test result: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
