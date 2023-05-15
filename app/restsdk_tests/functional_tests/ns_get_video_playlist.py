# -*- coding: utf-8 -*-
""" Negative Scenario Test for API: GET /v2/files/id/video/playlist (KAM-24292).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import requests
import sys
# platform modules
from middleware.arguments import InputArgumentParser
# test case
from restsdk_tests.functional_tests.ns_get_video_stream import NSGetVideoStreamTest


class NSGetVideoPlaylistTest(NSGetVideoStreamTest):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Negative: GET Video Playlist'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-24292'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def test(self):
        # Send request
        try:
            response = self.uut_owner.get_video_playlist(file_id=self.file_id, container='mpegTS',resolution=self.resolution)
        except requests.HTTPError, e:
            response = e.response

        self.verify_status_code(response)


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** NSGetVideoPlaylistTest test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/ns_get_video_playlist.py --uut_ip 10.136.137.159 -fn BMP2_PSP.mp4\
        """)
    parser.add_argument('-fid', '--file_id', help='Get remote file by file ID', metavar='ID')
    parser.add_argument('-fn', '--file_name', help='Get remote file by file Name', metavar='NAME')
    parser.add_argument('-pid', '--parent_id', help='ID of parent folder', metavar='ID')
    parser.add_argument('-pname', '--parent_name', help='Name of parent folder', metavar='Name')
    parser.add_argument('-r', '--resolution', help='The resolution of the returned transcoded video', default='original')

    test = NSGetVideoPlaylistTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
