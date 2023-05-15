# -*- coding: utf-8 -*-
""" Test for API: GET /v2/filesSearch/parents (KAM-16649).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
from pprint import pformat
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class SearchRootFolderTest(KDPTestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Search Root Folder'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KDP-825'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': True,
        'ssh_client': True
    }

    def declare(self):
        # Set default attributes
        self.parent_id = 'root'

    def test(self):
        items, next_page_token = self.uut_owner.search_file_by_parent(parent_id=self.parent_id)
        self.log.info('API Response: {}'.format(pformat(items)))
        # Test passed if it response HTTP status code 200


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Search_Root_Folder test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/search_root_folder.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-pid', '--parent_id', help='ID of parent folder', metavar='ID', default='root')

    test = SearchRootFolderTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
