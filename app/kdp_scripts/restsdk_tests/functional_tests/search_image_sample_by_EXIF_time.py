# -*- coding: utf-8 -*-
""" Test for API: GET /v2/filesSearch/mediaTimeSample (KAM-19243).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
from datetime import datetime
from pprint import pformat
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class SearchImageSampleByEXIFTimeTest(KDPTestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Search Image Sample By EXIF Time'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-19243'   # JIRA is inactive now.
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': True,
        'ssh_client': True
    }

    def declare(self):
        self.start_time = None
        self.end_time = None

    def init(self):
        if not all([self.start_time, self.end_time]):
            raise self.err.StopTest('Need start_time and end_time')

    def test(self):
        files = self.uut_owner.search_sample_file_by_time(
            start_time=self.start_time, end_time=self.end_time, mime_groups='image', limit=1000)
        self.log.info('API Response: \n{}'.format(pformat(files)))
        self.verify_result(files)

    def verify_result(self, files):
        result_pass = False
        start_time = datetime.strptime(self.start_time, '%Y-%m-%dT%H:%M:%S.%fZ')
        end_time = datetime.strptime(self.end_time, '%Y-%m-%dT%H:%M:%S.%fZ')

        # Only check all of iamge file exif data is in the range.
        for file in files:
            if not 'image' in file.get('mimeType', ''):
                continue # Not image ifle
            date_str = file.get('image', {}).get('date', None)
            if not date_str:
                continue # Image without EXIF data infotmation

            date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
            # Data time is not in the expected time range.
            if not (end_time >= date >= start_time):
                self.log.error('Current file :\n{}'.format(pformat(file)))
                result_pass = False
                break

            if not result_pass:
                result_pass = True

        if result_pass:
            self.log.info('Check response: PASSED')
        else:
            self.log.error('Check response: FAILED')
            raise self.err.TestFailure('Result is not correct')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Search_Image_Sample_By_EXIF_Time test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/search_image_sample_by_EXIF_time.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-st', '--start_time', help='Start time of range to search', metavar='TIME')
    parser.add_argument('-et', '--end_time', help='End time of range to search', metavar='TIME')

    test = SearchImageSampleByEXIFTimeTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
