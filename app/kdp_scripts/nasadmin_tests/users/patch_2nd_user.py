# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: PATCH /v2/user/{user-id} - 200 - 2nd user
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import json
import sys
import os
# platform modules
from middleware.arguments import KDPInputArgumentParser
from platform_libraries.test_utils import read_lines_to_string, run_test_with_data
from kdp_scripts.test_utils.test_case_utils import \
    nsa_declare_2nd_user, nsa_after_test_user, nsa_add_argument_2nd_user, nsa_init_2nd_user
from platform_libraries.assert_utls import nsa_assert_user_by_dict
# test case
from get_2nd_user import Get2ndUser


class Patch2ndUser(Get2ndUser):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Update user - 2nd user'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3413'

    def declare(self):
        nsa_declare_2nd_user(self)

    def test(self):
        nsa_init_2nd_user(self)
        token = self.nasadmin_2nd.login_with_cloud_token(cloud_token=self.rest_2nd.access_token)

        run_test_with_data(
            test_data=[
                (token['userID'], s) for s in \
                    read_lines_to_string(os.path.dirname(__file__) + '/../test_data/Patch2ndUser200.txt')],
            test_method=self.patch_user_test
        )

    def after_test(self):
        nsa_after_test_user(self)

    def patch_user_test(self, data):
        user_id = data[0]
        payload_str = data[1]
        payload = json.loads(payload_str)
        resp = self.nasadmin_2nd._update_user(user_id, payload_str)
        nsa_assert_user_by_dict(payload, resp, ignore_field_names=['spaceName', 'password'])
        resp = self.nasadmin_2nd.get_user(user_id)
        nsa_assert_user_by_dict(payload, resp, ignore_field_names=['spaceName', 'password'])
        if resp['localAccess'] is True:
            assert self.ssh_client.user_exists_in_kdp_system(user_name=resp['username'].encode('utf-8')), \
                'not found user in system'
            if payload.get('spaceName'):
                assert self.ssh_client.space_exists_in_smb_conf(space_name=payload['spaceName'].encode('utf-8')), \
                    'not found space in smb.conf'
                assert self.ssh_client.share_exists(share_name=payload['spaceName'].encode('utf-8')), \
                    'not found space share'
        elif resp['localAccess'] is False:
            if payload.get('spaceName'):
                assert not self.ssh_client.space_exists_in_smb_conf(space_name=payload['spaceName'].encode('utf-8')), \
                    'found space in smb.conf'
                assert not self.ssh_client.share_exists(share_name=payload['spaceName'].encode('utf-8')), \
                    'found space share'


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Patch user test for 2nd user ***
        """)
    nsa_add_argument_2nd_user(parser)

    test = Patch2ndUser(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
