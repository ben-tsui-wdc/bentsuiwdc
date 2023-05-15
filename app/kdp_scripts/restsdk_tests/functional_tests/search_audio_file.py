# -*- coding: utf-8 -*-
""" Test for API: GET /v2/filesSearch/audioTitle (KAM-19246).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
from pprint import pformat
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase


class SearchAudioFileTest(KDPTestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Search Audio File'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KDP-824'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': True,
        'ssh_client': True
    }

    def declare(self):
        self.file_name = None

    def test(self):
        files, _ = self.uut_owner.search_audio_file(limit=1000)
        self.log.info('API Response: \n{}'.format(pformat(files)))
        if self.file_name: self.verify_result(files)
        # Or Test passed if it response HTTP status code 200

    def verify_result(self, files):
        # Only check any of item name contain keyword.
        for file in files:
            file_name = file.get('name', '')
            if self.file_name == file_name:
                self.log.info('Check response: PASSED')
                return
        self.log.error('Check response: FAILED')
        raise self.err.TestFailure('Data not found')


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Search_Audio_File test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/search_audio_file.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-fn', '--file_name', help='File name to verify search result', metavar='NAME', default='')

    test = SearchAudioFileTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
