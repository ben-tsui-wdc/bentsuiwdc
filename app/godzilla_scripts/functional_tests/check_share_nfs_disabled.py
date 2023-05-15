# -*- coding: utf-8 -*-
""" Test case to disable share NFS access
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from godzilla_scripts.bat_scripts.nfs_rw_check import NFSRW


class CheckShareNFSDisabled(GodzillaTestCase):

    TEST_SUITE = 'Godzilla Sanity'
    TEST_NAME = 'Check Share NFS Disabled'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1431'
    PRIORITY = 'Critical'
    COMPONENT = 'Platform'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.share_folder = 'Public'

    def test(self):
        nfs_rw = NFSRW(self)
        nfs_rw.share_folder = self.share_folder
        nfs_rw.disable_share_nfs = True
        test_result = nfs_rw.main()
        if test_result:
            raise self.err.TestFailure('NFS RW test passed but it should have been failed!')
        else:
            self.log.info("NFS RW test failed as expected because it's disabled in the share folder")


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Add Public Share And Check Samba RW on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/functional_tests/check_share_ftp_disabled.py --uut_ip 10.136.137.159 -model PR2100\
        """)
    parser.add_argument('--share_folder', help='share folder to test nfs disable', default='Public')
    test = CheckShareNFSDisabled(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
