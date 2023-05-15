# -*- coding: utf-8 -*-
""" Test case to enable share NFS access
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from godzilla_scripts.bat_scripts.nfs_rw_check import NFSRW


class CheckShareNFSEnabled(GodzillaTestCase):

    TEST_SUITE = 'Godzilla Sanity'
    TEST_NAME = 'Check Share NFS Enabled'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1067'
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
        nfs_rw.disable_share_nfs = False
        nfs_rw.main()


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Add Public Share And Check Samba RW on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/functional_tests/check_share_nfs_enabled.py --uut_ip 10.136.137.159 -model PR2100\
        """)
    parser.add_argument('--share_folder', help='share folder to test nfs enable', default='Public')
    test = CheckShareNFSEnabled(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
