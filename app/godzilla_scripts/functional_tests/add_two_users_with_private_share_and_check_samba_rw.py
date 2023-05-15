# -*- coding: utf-8 -*-
""" Test case to Create 2 users and copy files to private folders
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from godzilla_scripts.bat_scripts.samba_rw_check import SambaRW


class AddTwoUsersWithPrivateShareAndCheckSambaRW(GodzillaTestCase):

    TEST_SUITE = 'Godzilla Sanity'
    TEST_NAME = 'Add Private Share And Check Samba RW'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1584'
    PRIORITY = 'Critical'
    COMPONENT = 'Platform'

    SETTINGS = {
        'uut_owner': False
    }

    def before_test(self):
        self.user_list = ['test_user1', 'test_user2']
        self.samba_rw = SambaRW(self)

    def test(self):
        self.log.info("Add new users and create private share folders, "
                      "the password and share folder name will be the same as the username, "
                      "and then run Samba RW test with specified user/folder")
        share_folders = self.ssh_client.get_share_permission()  # Used for check if share folder already exist
        for user in self.user_list:
            if not self.ssh_client.create_user(username=user):
                raise self.err.TestFailure('Create user and share folder failed!')

            if not self.ssh_client.change_share_public_status(share_name=user, public=False):
                raise self.err.TestFailure('Change share public status failed!')

            if not self.ssh_client.change_share_user_permission(share_name=user, user=user, permission=2):
                raise self.err.TestFailure('Change share user permission failed!')

            self.samba_rw.share_folder = user
            self.samba_rw.samba_user = user
            self.samba_rw.samba_password = user
            self.samba_rw.before_test()
            self.samba_rw.test()
            self.samba_rw.after_test()

    def after_test(self):
        for user in self.user_list:
            if not self.ssh_client.delete_share(share_name=user):
                raise self.err.TestFailure('Delete share folder: "{}" failed! '.format(user))

            if not self.ssh_client.delete_user(username=user):
                raise self.err.TestFailure('Delete user: "{}" failed! '.format(user))


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Create 2 users and copy files to private folders on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/functional_tests/add_two_users_with_private_share_and_check_samba_rw.py --uut_ip 10.136.137.159 -model PR2100\
        """)
    test = AddTwoUsersWithPrivateShareAndCheckSambaRW(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
