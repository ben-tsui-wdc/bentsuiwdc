# -*- coding: utf-8 -*-
""" Test case to delete share folder
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class DeleteShare(GodzillaTestCase):

    TEST_SUITE = 'Godzilla Sanity'
    TEST_NAME = 'Add And Delet Share Folder'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1177,GZA-1205'
    PRIORITY = 'Blocker'
    COMPONENT = 'Platform'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.share_folder = 'test_delete'

    def test(self):
        self.log.info("Checking if the test folder is already existing")
        share_folders = self.ssh_client.get_share_permission()  # Used for check if share folder already exist
        if self.share_folder not in share_folders.keys():
            self.log.warning("Cannot find test folder: {}, creating a new one now".format(self.share_folder))
            if not self.ssh_client.create_share(share_name=self.share_folder):
                raise self.err.TestFailure('Create share folder failed!')

        if not self.ssh_client.delete_share(share_name=self.share_folder):
            raise self.err.TestFailure('Delete share folder: "{}" failed! '.format(self.share_folder))


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Add Public Share And Check Samba RW on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/functional_tests/add_pubic_share_and_check_samba_rw.py --uut_ip 10.136.137.159 -model PR2100\
        """)
    parser.add_argument('--share_folder', help='User with rw access to test private folders', default='test_delete')
    test = DeleteShare(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
