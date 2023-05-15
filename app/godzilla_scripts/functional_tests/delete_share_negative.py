# -*- coding: utf-8 -*-
""" Test case to delete public share folder (negative test, public folder cannot be deleted)
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class DeleteShareNegative(GodzillaTestCase):
    """
        Todo: This test cannot be excuted now because the smbif cmd didn't block deleting the Public folder!
    """

    TEST_SUITE = 'Godzilla Sanity'
    TEST_NAME = 'Delet Public Share Folder (Negative)'
    # Popcorn
    PROJECT = 'godzilla'
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-32891'
    PRIORITY = 'major'
    COMPONENT = 'Platform'

    SETTINGS = {
        'uut_owner': False
    }

    def before_test(self):
        self.share_folder = 'Public'

    def test(self):
        self.log.info("Checking if the test folder is already existing")
        share_folders = self.ssh_client.get_share_permission()  # Used for check if share folder already exist
        if self.share_folder not in share_folders.keys():
            # Public folder should always existing in the device
            raise self.err.TestFailure('Cannot find the folder: {}!'.format(self.share_folder))

        if self.ssh_client.delete_share(share_name=self.share_folder):
            raise self.err.TestFailure('Delete folder successfully, but "{}" should never be deleted!'.format(self.share_folder))
        else:
            self.log.info("Delete folder: {} failed as expected".format(self.share_folder))


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Add Public Share And Check Samba RW on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/functional_tests/delete_share_negative.py --uut_ip 10.136.137.159 -model PR2100\
        """)
    test = DeleteShareNegative(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
