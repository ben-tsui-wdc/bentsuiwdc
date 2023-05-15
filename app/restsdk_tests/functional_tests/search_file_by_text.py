# -*- coding: utf-8 -*-
""" Test for API: GET /v2/filesSearch/text (KAM-18422).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
from pprint import pformat
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class SearchFileByTextTest(TestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Search File By Text'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-18422'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.keyword = None

    def init(self):
        if not self.keyword:
            raise self.err.StopTest('Need keyword')

    def test(self):
        items, page_token = self.uut_owner.search_file_by_text(keyword=self.keyword)
        self.log.info('API Response: {}'.format(pformat(items)))
        self.verify_result(items)
    
    def verify_result(self, items):
        # Only check any of item name contain keyword.
        for item in items:
            data = item.get('file', {})
            data_name = data.get('name', '')
            if self.keyword in data_name:
                self.log.info('Check data name: PASSED')
                return
        self.log.error('Check data name: FAILED')
        raise self.err.TestFailure('Data not found')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Search_File_By_Text test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/search_file_by_text.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-k', '--keyword', help='Keyword of name to search', metavar='TEXT', default='')

    test = SearchFileByTextTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
