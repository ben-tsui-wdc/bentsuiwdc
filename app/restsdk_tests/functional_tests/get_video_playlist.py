# -*- coding: utf-8 -*-
""" Test for API: GET /v2/files/id/video/playlist (KAM-20141).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import os
import sys
# platform modules
from middleware.arguments import InputArgumentParser
from platform_libraries.pyutils import save_to_file
# test case
from restsdk_tests.functional_tests.get_video_stream import GetVideoStreamTest


class GetVideoPlaylistTest(GetVideoStreamTest):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'GET Video Playlist'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = 'KAM-20141'
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    def test(self):
        # Request video playlist to transcode matroska format and specified resolution.
        response = self.uut_owner.get_video_playlist(file_id=self.file_id, container='mpegTS', resolution=self.resolution)
        M3U8_content = response.content
        self.log.info('M3U8 Content: \n{}'.format(M3U8_content))
        self.verify_M3U8_header(response)
        self.verify_M3U8_content(M3U8_content)

        # Verify each video link.
        for video_link in self.split_video_link(M3U8_content):
            self.log.info('Verify link: {}'.format(video_link))
            try:
                video_response = self._send_request(file_id=self.file_id, video_link=video_link)
                save_to_file(iter_obj=video_response.iter_content(chunk_size=1024), file_name=self.local_file)
                self.verify_header(video_response, content_type='video/mp2t')
                self.verify_content(video_format='MPEG-TS')
            finally:
                self.adb.is_any_FFmpeg_running() # just to check status again.
                if os.path.exists(self.local_file):
                    os.remove(self.local_file)

    def verify_M3U8_header(self, response):
        # Response M3U8 headers should be 'application/x-mpegURL'.
        if 'application/x-mpegURL' != response.headers['Content-Type']:
            self.log.info('Verify M3U8 header: FAILED.')
            raise self.err.TestFailure('Response M3U8 header is incorrect.')
        self.log.info('Verify M3U8 header: PASSED.')

    def verify_M3U8_content(self, content):
        # First line of content should be "#EXTM3U"
        if not content.startswith('#EXTM3U'):
            self.log.info('Verify M3U8 content header: FAILED.')
            raise self.err.TestFailure('Response M3U8 content header is incorrect.')
        self.log.info('Verify M3U8 content header: PASSED.')

    def split_video_link(self, content):
        split_list = content.split('#EXTINF:')
        for EXTINF_part in split_list[1:]: # skip first part (EXT-X part).
            duration_part, link_part = EXTINF_part.split('\n')[:2] # only fetch the first two values.
            # => '9.32'
            duration = duration_part.strip(',')
            # => '/video?access_token=XX.XX.XX-XX-XX-XX-XX-XX-XX&container=matroska&duration=9319&resolution=original&startOffset=0'
            link = link_part.lstrip('.')
            yield link

    def _send_request(self, file_id, video_link):
        """ Send video stream request via restAPI lib. """
        response = self.uut_owner.send_request(
            method='GET',
            url='http://{0}/sdk/v2/files/{1}{2}'.format(self.uut_owner.uut_ip, file_id, video_link),
        )
        if response.status_code != 200:
            self.uut_owner.error('Fail to execute get video stream.', response)
        return response


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** GET_Video_Playlist test on Kamino Android ***
        Examples: ./run.sh restsdk_tests/functional_tests/get_video_playlist.py --uut_ip 10.136.137.159 -fn BMP2_PSP.mp4\
        """)
    parser.add_argument('-fid', '--file_id', help='Get remote file by file ID', metavar='ID')
    parser.add_argument('-fn', '--file_name', help='Get remote file by file Name', metavar='NAME')
    parser.add_argument('-pid', '--parent_id', help='ID of parent folder', metavar='ID')
    parser.add_argument('-pname', '--parent_name', help='Name of parent folder', metavar='Name')
    #parser.add_argument('-vf', '--video_format', help='The format of the returned transcoded video', default='mpegTS')
    parser.add_argument('-r', '--resolution', help='The resolution of the returned transcoded video', default='original')

    test = GetVideoPlaylistTest(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
