# -*- coding: utf-8 -*-
""" Endpoint Test Scenario: PATCH /v2/user/{user-id} - 200 - Owner user
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# std modules
import json
import sys
import os
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.test_utils import read_lines_to_string, run_test_with_data
from platform_libraries.assert_utls import nsa_assert_user_by_dict
from platform_libraries.test_utils import run_test_with_suit, exec_filter


class PatchUser(KDPTestCase):

    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'Update user - Owner user'
    # Popcorn
    TEST_JIRA_ID = 'KDP-3413'

    def declare(self):
        self.exec_test = None

    def test(self):
        token = self.nasadmin.login_owner()
        run_test_with_suit(
            test_suit=exec_filter(
                exec_list=[
                    # set owner info to default at end of test
                    (self.patch_user_test_with_dataset, {'user_id': token['userID']}),
                    (self.patch_user_test_for_duplicated_space_name, {'user_id': token['userID']})
                ],
                filter_names=self.exec_test # for specifying sub-tests to execute
            )
        )

    def patch_user_test_with_dataset(self, user_id):
        run_test_with_data(
            test_data=[
                (user_id, s) for s in \
                    read_lines_to_string(os.path.dirname(__file__) + '/../test_data/PatchUser200.txt')],
            test_method=self.patch_user_test
        )

    def patch_user_test(self, data_tuple):
        user_id = data_tuple[0]
        payload_str = data_tuple[1]
        payload = json.loads(payload_str)
        resp = self.nasadmin._update_user(user_id, payload_str)
        nsa_assert_user_by_dict(payload, resp, ignore_field_names=['spaceName', 'password'])
        resp = self.nasadmin.get_user(user_id)
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

    def patch_user_test_for_duplicated_space_name(self, user_id):
        # expected without error
        owner_cloud_user = self.uut_owner.get_cloud_user()
        self.nasadmin.update_user(user_id, spaceName=owner_cloud_user['user_metadata']['first_name'])


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Patch user test ***
        """)
    parser.add_argument('-et', '--exec_test', nargs='+', \
                        help='method names to execute. e.g. -et t1 t2 t3', default=None)

    test = PatchUser(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
