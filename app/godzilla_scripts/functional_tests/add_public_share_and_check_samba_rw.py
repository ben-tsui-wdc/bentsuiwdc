# -*- coding: utf-8 -*-
""" Test case to Add Public Share And Check Samba RW
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from godzilla_scripts.bat_scripts.samba_rw_check import SambaRW


class AddPublicShareAndCheckSambaRW(GodzillaTestCase):

    TEST_SUITE = 'Godzilla Sanity'
    TEST_NAME = 'Add Public Share And Check Samba RW'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1473, GZA-1430'
    PRIORITY = 'Blocker'
    COMPONENT = 'Platform'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.keep_folder = False
        self.samba_user = None
        self.samba_password = None

    def before_test(self):
        self.share_folder = "new_public"

    def test(self):
        if not self.ssh_client.create_share(share_name=self.share_folder, public=True):
            raise self.err.TestFailure('Create share folder failed!')
        samba_rw = SambaRW(self)
        samba_rw.share_folder = self.share_folder
        samba_rw.samba_user = self.samba_user
        samba_rw.samba_password = self.samba_password
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
    parser.add_argument('--samba_user', help='Samba login user name', default=None)
    parser.add_argument('--samba_password', help='Samba login password', default=None)
    parser.add_argument('--keep_folder', help='Do not delete folder after testing', action='store_true', default=False)
    test = AddPublicShareAndCheckSambaRW(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
