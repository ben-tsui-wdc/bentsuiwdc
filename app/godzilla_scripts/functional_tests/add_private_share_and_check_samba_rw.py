# -*- coding: utf-8 -*-
""" Test case to Add Private Share And Check Samba RW
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from godzilla_scripts.bat_scripts.samba_rw_check import SambaRW


class AddPrivateShareAndCheckSambaRW(GodzillaTestCase):

    TEST_SUITE = 'Godzilla Sanity'
    TEST_NAME = 'Add Private Share And Check Samba RW'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1383'
    PRIORITY = 'Critical'
    COMPONENT = 'Platform'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.username_rw = 'admin'
        self.password_rw = 'adminadmin'
        self.username_deny = 'second_user'
        self.password_deny = 'second_user'
        self.keep_folder = False

    def before_test(self):
        self.share_folder = "new_private"

    def test(self):
        if not self.ssh_client.create_share(share_name=self.share_folder):
            raise self.err.TestFailure('Create share folder failed!')

        if not self.ssh_client.change_share_public_status(share_name=self.share_folder, public=False):
            raise self.err.TestFailure('Change share public status failed!')

        if not self.ssh_client.change_share_user_permission(share_name=self.share_folder, user='admin', permission=2):
            raise self.err.TestFailure('Change share user permission failed!')

        self.log.warning("Negative test: try to run samba rw test with user that has no permission")
        samba_rw = SambaRW(self)
        samba_rw.share_folder = self.share_folder
        try:
            samba_rw.samba_user = self.username_deny
            samba_rw.samba_password = self.password_deny
            samba_rw.before_test()
            samba_rw.test()
            samba_rw.after_test()
        except Exception as e:
            self.log.info("Test failed as expected! Error: {}".format(repr(e)))

        self.log.warning("Positive test: try to run samba rw test with user that has permission")
        samba_rw.samba_user = self.username_rw
        samba_rw.samba_password = self.password_rw
        samba_rw.before_test()
        samba_rw.test()
        samba_rw.after_test()

    def after_test(self):
        if not self.keep_folder:
            if not self.ssh_client.delete_share(share_name=self.share_folder):
                raise self.err.TestFailure('Delete share folder: "{}" failed! '.format(self.share_folder))


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Add Public Share And Check Samba RW on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/functional_tests/add_pubic_share_and_check_samba_rw.py --uut_ip 10.136.137.159 -model PR2100\
        """)
    parser.add_argument('--username_rw', help='User with rw access to test private folders', default='admin')
    parser.add_argument('--password_rw', help='Password of rw access user', default='adminadmin')
    parser.add_argument('--username_deny', help='User with deny access to test private folder', default='second_user')
    parser.add_argument('--password_deny', help='Password of deny access user', default='second_user')
    parser.add_argument('--keep_folder', help='Do not delete folder after testing', action='store_true', default=False)
    test = AddPrivateShareAndCheckSambaRW(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
