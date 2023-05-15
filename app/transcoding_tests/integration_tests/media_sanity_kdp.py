# -*- coding: utf-8 -*-
""" Media Sanity Test for KDP.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import copy
import os
import sys
import time
from collections import OrderedDict
from pprint import pformat
from uuid import uuid4
# platform modules
from middleware.kdp_integration_test import KDPIntegrationTest
from middleware.arguments import KDPIntegrationTestArgument
from platform_libraries.compare import local_md5sum, md5sum
from platform_libraries.constants import Kamino
from platform_libraries.popcorn import PopcornTest
from platform_libraries.pyutils import retry, save_to_file
# test modules
from transcoding_tests.lib.converter import TranscodingSettingInformation
from transcoding_tests.lib.transcoding_settings import (
    API_TRANSCODING_SETTINGS, get_max_api_resolution_options
)
# tests
from restsdk_transcoding import add_errmsg_header
from godzilla_scripts.integration_tests.media_sanity import sub_test_handler, MediaSanityTest
# 3rd party modules
import requests


#
# Test Implements
#
class KDPMediaSanityTest(KDPIntegrationTest, MediaSanityTest):

    TEST_SUITE = 'RESTSDK Transcoding'
    TEST_NAME = 'Media Sanity Test'
    COMPONENT = 'PLATFORM'

    # Popcorn
    PROJECT = 'Keystone Device Platform'
    TEST_TYPES = 'Functional'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    REPORT_NAME = 'SANITY'

    TEST_JIRA_ID_MAPPING = {
       "Video Extraction Test": "KDP-613",
       "checkOnly call Test": "KDP-642",
       "MKV Transcoding Test": "KDP-605",
       "HLS Playlist Test": "KDP-1923",
       "Video Segment Test": "KDP-607"
    }
    ISSUE_JIRA_ID_MAPPING = {
    }

    def declare(self):
        super(MediaSanityTest, self).declare()
        self.fixed_platform_for_check_call = None
        self.transcoding_request_timeout = 60*5
        self.fixed_target_resolution = None

    def init(self):
        self.replace_kdp_methods()
        super(MediaSanityTest, self).init()

    def replace_kdp_methods(self):
        self.ssh_client.is_any_FFmpeg_running = self.ssh_client.is_any_FFmpeg_running_kdp
        self.ssh_client.kill_first_found_FFmpeg = lambda *args: None # disable
        if self.no_wait_ffmpeg:
            def no_wait(*args, **kwargs):
                self.log.info('No wait for ffmpeg process')
                self.ssh_client.is_any_FFmpeg_running_kdp()
                return True
            self.ssh_client.wait_all_FFmpeg_finish = no_wait

    def test(self):
        # Change target for RnD
        if 'rocket' in self.uut['model'] or 'drax' in self.uut['model']:
            #target_codec = 'hevc'
            target_codec = 'h264'
        else:
            target_codec = 'h264'

        # Init global_dict.
        self.global_dict = OrderedDict([
            ('task_idx', 0),
            ('test_info', None),
            ('transcoding_setting', None),
            ('export_to_csv', False),
            ('sub_test_results', [])
        ])

        # Walk user root from top to bottom.
        for retval in self.walk_on_nas():
            self.video_is_supported = False

            # Update test_info.
            self.global_dict['test_info'] = self.gen_test_info(rest_item=retval)
            if not self.global_dict['test_info']:
                continue

            # [Test For REST SDK Extraction]
            self.run_sub_test(sub_name='Video Extraction Test', test_method=self.test_extraction)

            transcoding_duration = self.get_max_video_duration()
            # specifying target resolution
            if self.fixed_target_resolution:
                resolution = self.fixed_target_resolution
            else:
                resolution = self.get_small_resolution(video_info=self.global_dict['test_info']['rotated_prepared_info'])
            self.log.info('To ' + resolution)

            # Set transcoding setting
            self.global_dict['transcoding_setting'] = TranscodingSettingInformation(target_codec, 'matroska', resolution, transcoding_duration)

            # [Test For Check Only Call]
            #self.run_sub_test(sub_name='checkOnly call Test', test_method=self.test_check_only_call)
            self.run_sub_test(sub_name='checkOnly call Test - ' + resolution.upper(), test_method=self.test_check_only_call)
            if not self.video_is_supported:
                self.log.warning('Since video/transcoding not supported, do the next case...')
                self.log.warning('{} is PASS'.format(self.global_dict['test_info']['case_name']))
                continue

            self.clean_ffmpeg_logs()
            # [Test For Video Transcoding]
            self.run_sub_test(sub_name='MKV Transcoding Test - ' + resolution.upper(), test_method=self.test_media_transcoding)

            # Set transcoding setting
            #if self.uut['model'] in ['yodaplus']:
            #    rest_d = self.global_dict['test_info']['rest_info']['video']['duration']
            #    self.global_dict['transcoding_setting'] = TranscodingSettingInformation('h264', 'mpegTS', resolution, 5*60*1000 if rest_d >= 5*60 else int(rest_d)*1000)
            #else:
            self.global_dict['transcoding_setting'] = TranscodingSettingInformation(target_codec, 'mpegTS', resolution, transcoding_duration)

            self.clean_ffmpeg_logs()
            # [Test For HLS playlist]
            self.run_sub_test(sub_name='HLS Playlist Test - ' + resolution.upper(), test_method=self.test_video_playlist)

            # [Test For Video Segment]
            self.run_sub_test(sub_name='Video Segment Test - ' + resolution.upper(), test_method=self.test_video_segment)

    def get_small_resolution(self, video_info):
        resolution = get_max_api_resolution_options(video_info)
        if '1080p' in resolution:
            return '720p'
        elif '720p' in resolution:
            return '480p'
        elif '480p' in resolution:
            return '360p'
        elif '360p' in resolution:
            return '240p'
        else:
            self.log.warning('Unknown resolution')
            return '720p'

    def done_log(self, name_postfix):
        """ Export and upload logs. """
        if not self.not_export_device_log:
            self.data.export_kdp_logs(
                clean_device_logs=self.clean_device_logs, name_postfix=name_postfix, device_tmp_log=self.env.device_tmp_log)

    def clean_ffmpeg_logs(self):
        self.log.info('Clean FFmpeg logs')
        self.ssh_client.execute_cmd('echo "" > /var/log/wdlog.log')
        self.ssh_client.execute_cmd('echo "" > /var/log/wdpublic.log')
        self.ssh_client.execute_cmd('echo "" > /var/log/analyticprivate.log')
        self.ssh_client.execute_cmd('echo "" > /var/log/analyticpublic.log')
        self.ssh_client.execute_cmd('echo "" > /var/log/kern.log')

if __name__ == '__main__':
    parser = KDPIntegrationTestArgument("""\
        *** MediaSanityTest on KDP ***
        Examples: ./run.sh transcoding_tests/integration_tests/media_sanity_kdp.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-db_path', '--db_file_path', help='Path of db file', metavar='PATH')
    parser.add_argument('-db_url', '--db_file_url', help='URL of db file to download from file server', metavar='URL')
    parser.add_argument('-duration', '--duration', help='Duration value to convent all test video', type=int, metavar='DURATION', default=None)
    parser.add_argument('-nid', '--not_init_data', help='Use existing data for test', action='store_true', default=False)
    parser.add_argument('-nedl', '--not_export_device_log', help="Don't export device logs at end of each sub-test", action='store_true', default=False)
    #parser.add_argument('-nuel', '--not_upload_end_log', help="Don't upload logs to sumologic at end of each sub-test", action='store_true', default=False)
    parser.add_argument('-csf', '--case_start_from', help="Sub-case number start from", type=int, metavar='NUMBER', default=0)
    parser.add_argument('-ldp', '--local_data_path', help="Upload test video from local path via RestSDK call")
    parser.add_argument('-rizf', '--reboot_if_zombie_found', help="Reboot device when zombie process found", action='store_false', default=True)
    parser.add_argument('-video_url', '--video_file_url', help='Path of test video files', metavar='PATH')
    parser.add_argument('-cdl', '--clean_device_logs', help='Clean device logs after exporting', action='store_true', default=False)
    parser.add_argument('-rtt', '--retry_time_transcode', help='Retry time for transcoding call', type=int, metavar='MAX', default=0)
    parser.add_argument('-rtvp', '--retry_time_video_playlist', help='Retry time for playlist call', type=int, metavar='MAX', default=6)
    parser.add_argument('-rtvs', '--retry_time_video_segment', help='Retry time for video segment call', type=int, metavar='MAX', default=5)
    parser.add_argument('-kv', '--keep_video', help='keep all transcoded video', action='store_true', default=False)
    parser.add_argument('-trt', '--transcoding_request_timeout', help='Transcoding request timeout', type=int, metavar='SECS', default=60*5)
    parser.add_argument('-ftr', '--fixed_target_resolution', help='Fixed target resolution', metavar='RES', default=False)
    parser.add_argument('-nwf', '--no_wait_ffmpeg', help='Do not wait for device idle before a new test', action='store_true', default=False)
    parser.add_argument('-wfz', '--wait_for_zombie', help='Wait for zombie exit', action='store_true', default=False)
    parser.add_argument('-wfpr', '--wait_for_pretranscoding_ready', help='keep all transcoded video', action='store_true', default=False)

    test = KDPMediaSanityTest(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
