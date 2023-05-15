# -*- coding: utf-8 -*-
""" Test for API: GET /v2/filesSearch/parentAndName (KAM-16648).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
from pprint import pformat
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class SearchFileByNameTest(TestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Search File By Name'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-16648'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.name = None

    def init(self):
        if not self.name:
            raise self.err.StopTest('Need name')

    def test(self):
        items, elapsed = self.uut_owner.search_file_by_parent_and_name(name=self.name)
        self.log.info('API Response: {}'.format(pformat(items)))
        # Test passed if it response HTTP status code 200


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Search_File_By_Name test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/search_file_by_name.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-n', '--name', help='Name of file/folder to search', metavar='NAME', default='')

    test = SearchFileByNameTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
