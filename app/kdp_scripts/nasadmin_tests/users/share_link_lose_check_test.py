# -*- coding: utf-8 -*-
""" Share link lose test
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from kdp_scripts.test_utils.test_case_utils import \
    nsa_add_argument_2nd_user, nsa_declare_2nd_user, nsa_after_test_user, nsa_init_2nd_user


class ShareLinkLoseTest(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'KDP-5847 - share link lose test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-5847'

    def declare(self):
        nsa_declare_2nd_user(self)
        self.space_name_owner = 'automation'
        self.space_name_user2nd = 'user2nd'

    def test(self):
        owner_token = self.nasadmin.login_owner()
        nsa_init_2nd_user(self)
        user_2nd_token = self.nasadmin_2nd.login_with_cloud_token(cloud_token=self.rest_2nd.access_token)

        try:
            self.log.info('Enabling local access to owner')
            self.nasadmin.update_user(
                owner_token['userID'], localAccess=True, username="owner", password="password")
            self.log.info('Enabling local access to 2nd user with spaceName=user2nd')
            self.nasadmin_2nd.update_user(
                user_2nd_token['userID'], localAccess=True, username="user2nd", password="password",
                spaceName=self.space_name_user2nd)
            exit_status, output = self.ssh_client.execute('ls /shares/')
            if not output or len(output.split()) != 2:
                raise self.err.StopTest('The number of share links is not as expected')
            assert self.space_name_owner in output, 'Not found share link for owner'
            assert self.space_name_user2nd in output, 'Not found share link for 2nd user'
        finally:
            self.log.info('Recovering users information')
            self.nasadmin.update_user(owner_token['userID'], localAccess=False, username="", password="")
            self.nasadmin_2nd.update_user(user_2nd_token['userID'], localAccess=False, username="", password="")

    def after_test(self):
        nsa_after_test_user(self)


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Share link lose test ***
        """)
    nsa_add_argument_2nd_user(parser)

    test = ShareLinkLoseTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
