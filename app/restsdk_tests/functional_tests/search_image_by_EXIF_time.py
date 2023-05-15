# -*- coding: utf-8 -*-
""" Test for API: GET /v2/filesSearch/mediaTime (KAM-19245).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
from datetime import datetime
from pprint import pformat
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
# test case
from restsdk_tests.functional_tests.search_image_sample_by_EXIF_time import SearchImageSampleByEXIFTimeTest


class SearchImageByEXIFTimeTest(SearchImageSampleByEXIFTimeTest):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Search Image By EXIF Time'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-19245'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def test(self):
        files, next_page = self.uut_owner.search_file_by_time(
            start_time=self.start_time, end_time=self.end_time, mime_groups='image', limit=1000)
        self.log.info('API Response: \n{}'.format(pformat(files)))
        self.verify_result(files)


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Search_Image_By_EXIF_Time test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/search_image_by_EXIF_time.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-st', '--start_time', help='Start time of range to search', metavar='TIME')
    parser.add_argument('-et', '--end_time', help='End time of range to search', metavar='TIME')

    test = SearchImageByEXIFTimeTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
