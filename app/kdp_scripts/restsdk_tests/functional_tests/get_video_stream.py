# -*- coding: utf-8 -*-
""" Test for API: GET /v2/files/id/video (KAM-20139).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
from pprint import pformat
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.mediainfo import MediaInfo
from platform_libraries.pyutils import save_to_file
from platform_libraries.common_utils import execute_local_cmd
# test case
from kdp_scripts.restsdk_tests.functional_tests.get_data_by_id import GetDataByIDTest


class GetVideoStreamTest(GetDataByIDTest):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Get Matroska Video Stream'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KDP-644'
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
        self.local_file = 'test_file' # temple file to save video stram data.
        self.expect_content_type = 'video/x-matroska' # String to verify response header. (video/mp4)
        self.expect_video_format = 'Matroska' # String to verify video format.
        self.expect_video_codec = None # String to verify video codec.
        self.expect_video_resolution = None # XXXp string to verify video resolution.
        self.expect_video_width = None # width or height to verify video resolution.
        self.expect_video_height = None
        self.quick_test = True # Just transcode a short video instead of whole source.
        self.request_timeout = 60*5
        self.recorder_dict = None # For access data from other code.

    def init(self):
        if not self.file_name and not self.file_id:
            raise self.err.StopTest('Need file_name or file_id')

    def before_test(self):
        if self.file_id:
            return
        self.parent_id = self.get_parent_id()
        self.file_id = self.get_data_id(name=self.file_name, parent_id=self.parent_id)

    def test(self):
        if not self.ssh_client.wait_all_FFmpeg_finish(delay=10, timeout=60*60):
            self.log.error('Timeout waiting for FFmpeg processes finish.')

        try:
            # Request video stream to transcode matroska format and specified resolution(resolution seems useless).
            response = self.uut_owner.get_video_stream(file_id=self.file_id, container=self.video_format, resolution=self.resolution,
                video_codec=self.video_codec, duration='5000' if self.quick_test else None, timeout=self.request_timeout)
            save_to_file(iter_obj=response.iter_content(chunk_size=1024), file_name=self.local_file)
            self.verify_header(response, content_type=self.expect_content_type)
            self.verify_content(self.expect_video_format, self.expect_video_codec, self.expect_video_resolution,
                self.expect_video_width, self.expect_video_height)
        finally:
            self.ssh_client.is_any_FFmpeg_running() # just to check status again.
            if os.path.exists(self.local_file):
                os.remove(self.local_file)

    def verify_header(self, response, content_type='video/x-matroska'):
        # Response headers should be 'video/x-matroska'.
        self.log.info("Response Header: \n{}".format(pformat(response.headers)))
        if content_type.lower() != response.headers.get('Content-Type', '').lower():
            self.log.info('Verify header: FAILED.')
            self.uut_owner.log_response(response, logger=self.log.warning)
            with open(self.local_file) as f:
                self.log.warning('Response content(one line): {}'.format(f.readline()))
            raise self.err.TestFailure('Response header is incorrect.')
        self.log.info('Verify header: PASSED.')

    def verify_content(self, video_format='Matroska', video_codec=None, video_resolution=None, video_width=None,
            video_height=None):
        file_info = MediaInfo(filename=self.local_file, shell_exe=execute_local_cmd)
        # Video content should be 'Matroska' format.
        if video_format:
            if not file_info.verify_video_format(video_format):
                self.log.info('Verify format: FAILED.')
                raise self.err.TestFailure('Content format is incorrect.')
            self.log.info('Verify format: PASSED.')
        if video_codec:
            if not file_info.verify_video_codec(video_codec):
                self.log.info('Verify Codec: FAILED.')
                raise self.err.TestFailure('Content Codec is incorrect.')
            self.log.info('Verify Codec: PASSED.')
        if video_resolution:
            if not file_info.verify_resolution(video_resolution):
                self.log.info('Verify Resolution: FAILED.')
                raise self.err.TestFailure('Content Resolution is incorrect.')
            self.log.info('Verify Resolution: PASSED.')
        if video_width or video_height:
            if not file_info.verify_width_and_height(width=video_width, height=video_height):
                self.log.info('Verify Resolution: FAILED.')
                raise self.err.TestFailure('Content Resolution is incorrect.')
            self.log.info('Verify Resolution: PASSED.')

        # Record the MediaInfo information for output file.
        self.record_mediainfo(file_info)

    def record_mediainfo(self, file_info):
        """ Save info to self.recorder_dict """
        if isinstance(self.recorder_dict, dict):
            self.recorder_dict['after'] = file_info.raw_info


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** GET_Video_Stream test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/get_video_stream.py --uut_ip 10.136.137.159 -fn BMP2_PSP.mp4\
        """)
    parser.add_argument('-fid', '--file_id', help='Get remote file by file ID', metavar='ID')
    parser.add_argument('-fn', '--file_name', help='Get remote file by file Name', metavar='NAME')
    parser.add_argument('-pid', '--parent_id', help='ID of parent folder', metavar='ID')
    parser.add_argument('-pname', '--parent_name', help='Name of parent folder', metavar='Name')
    parser.add_argument('-vc', '--video_codec', help='The codec of the returned transcoded video', default='h264')
    parser.add_argument('-vf', '--video_format', help='The format of the returned transcoded video', default='matroska')
    parser.add_argument('-r', '--resolution', help='The resolution of the returned transcoded video', default='original')
    parser.add_argument('-ect', '--expect_content_type', help='The content type to verify response header', default='video/x-matroska')
    parser.add_argument('-evf', '--expect_video_format', help='The video format to verify returned transcoded video', default='Matroska')
    parser.add_argument('-evc', '--expect_video_codec', help='The codec value to verify returned transcoded video', default=None)
    parser.add_argument('-evr', '--expect_video_resolution', help='The resolution value to verify returned transcoded video', default=None)
    parser.add_argument('-evw', '--expect_video_width', help='The width value to verify returned transcoded video', type=int, default=None)
    parser.add_argument('-evh', '--expect_video_height', help='The height value to verify returned transcoded video', type=int, default=None)
    parser.add_argument('-qt', '--quick_test', help='Run test in quick mode', type=int, default=None)

    test = GetVideoStreamTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
