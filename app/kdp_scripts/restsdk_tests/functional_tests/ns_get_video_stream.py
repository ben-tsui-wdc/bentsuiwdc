# -*- coding: utf-8 -*-
""" Negative Scenario Test for API: GET /v2/files/id/video (KAM-24291).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import requests
import sys
from pprint import pformat
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
# test case
from restsdk_tests.functional_tests.get_data_by_id import GetDataByIDTest


class NSGetVideoStreamTest(GetDataByIDTest):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Negative: GET Video Stream'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-24291'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def declare(self):
        self.file_id = None # Use file_id or file_name to get file
        self.file_name = None
        self.parent_id = None # Use parent_id or parent_name to set parent ID
        self.parent_name = None
        self.video_codec = 'h264' # video_codec to transcode.
        self.video_format = 'matroska' # video_format to transcode.
        self.resolution = 'original' # resolution to transcode.
        self.request_timeout = 60*5

    def init(self):
        if not self.file_name and not self.file_id:
            raise self.err.StopTest('Need file_name or file_id')

    def before_test(self):
        if self.file_id:
            return
        self.parent_id = self.get_parent_id()
        self.file_id = self.get_data_id(name=self.file_name, parent_id=self.parent_id)

    def test(self):
        if not self.adb.wait_all_FFmpeg_finish(delay=10, timeout=24*60*60):
            self.log.error('Timeout waiting for FFmpeg processes finish.')
        # Send request
        try:
            response = self.uut_owner.get_video_stream(file_id=self.file_id, container=self.video_format, resolution=self.resolution,
                video_codec=self.video_codec, timeout=self.request_timeout)
        except requests.HTTPError, e:
            response = e.response

        self.verify_status_code(response)

    def verify_status_code(self, response):
        if response.status_code != 500:
            raise self.err.TestFailure('Response status code: {} is incorrect.'.format(response.status_code))
        self.log.info('Verify status code: PASSED.')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** NSGetVideoStreamTest test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/ns_get_video_stream.py --uut_ip 10.136.137.159 -fn BMP2_PSP.mp4\
        """)
    parser.add_argument('-fid', '--file_id', help='Get remote file by file ID', metavar='ID')
    parser.add_argument('-fn', '--file_name', help='Get remote file by file Name', metavar='NAME')
    parser.add_argument('-pid', '--parent_id', help='ID of parent folder', metavar='ID')
    parser.add_argument('-pname', '--parent_name', help='Name of parent folder', metavar='Name')
    parser.add_argument('-vc', '--video_codec', help='The codec of the returned transcoded video', default='h264')
    parser.add_argument('-vf', '--video_format', help='The format of the returned transcoded video', default='matroska')
    parser.add_argument('-r', '--resolution', help='The resolution of the returned transcoded video', default='original')

    test = NSGetVideoStreamTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
