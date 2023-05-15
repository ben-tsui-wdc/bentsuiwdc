# -*- coding: utf-8 -*-
""" Test case to enable Share FTP access
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from godzilla_scripts.bat_scripts.ftp_rw_check import FTPRW


class CheckShareFTPEnabled(GodzillaTestCase):

    TEST_SUITE = 'Godzilla Sanity'
    TEST_NAME = 'Check Share FTP Enabled'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1348'
    PRIORITY = 'Critical'
    COMPONENT = 'Platform'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        self.share_folder = 'Public'

    def test(self):
        ftp_rw = FTPRW(self)
        ftp_rw.share_folder = self.share_folder
        ftp_rw.disable_share_ftp = False
        ftp_rw.main()


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Add Public Share And Check Samba RW on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/functional_tests/check_share_ftp_enabled.py --uut_ip 10.136.137.159 -model PR2100\
        """)
    parser.add_argument('--share_folder', help='share folder to test ftp enable', default='Public')
    test = CheckShareFTPEnabled(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
