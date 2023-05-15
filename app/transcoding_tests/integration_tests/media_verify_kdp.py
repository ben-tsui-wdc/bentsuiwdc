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
from platform_libraries.common_utils import check_port_pingable
from platform_libraries.constants import Kamino
from platform_libraries.popcorn import PopcornTest
from platform_libraries.pyutils import retry, save_to_file
# test modules
from transcoding_tests.lib.converter import TranscodingSettingInformation
from transcoding_tests.lib.transcoding_settings import API_TRANSCODING_SETTINGS
# tests
from restsdk_transcoding import add_errmsg_header
from godzilla_scripts.integration_tests.media_sanity import MediaSanityTest
# 3rd party modules
import requests


#
# Test Implements
#
class KDPMediaSanityTest(KDPIntegrationTest, MediaSanityTest):

    TEST_SUITE = 'RESTSDK Transcoding'
    TEST_NAME = 'Media Sanity Test'
    REPORT_NAME = 'Sanity'

    COMPONENT = 'PLATFORM'
    TEST_JIRA_ID_MAPPING = {
       "Video Extraction Test": "KDP-613",
       "checkOnly call Test": "KDP-642",
       "MKV Transcoding Test": "KDP-605",
       "HLS Playlist Test": "KDP-1923",
       "Video Segment Test": "KDP-607"
    }
    ISSUE_JIRA_ID_MAPPING = {
    }

    def replace_kdp_methods(self):
        self.ssh_client.is_any_FFmpeg_running = self.ssh_client.is_any_FFmpeg_running_kdp

    def declare(self):
        super(MediaSanityTest, self).declare()
        self.fixed_platform_for_check_call = None
        self.transcoding_request_timeout = 60*5

    def test(self):
        self.replace_kdp_methods()

        self.uut_owner._retry_times = 0

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
            # Update test_info.

            self.global_dict['test_info'] = self.gen_test_info(rest_item=retval)
            if not self.global_dict['test_info']:
                continue

            # [Test For REST SDK Extraction]
            #self.run_sub_test(sub_name='Video Extraction Test', test_method=self.test_extraction)

            #self.reboot()
            #time.sleep(60)
            # Set transcoding setting
            self.global_dict['transcoding_setting'] = TranscodingSettingInformation('h264', 'matroska', '720p', self.duration)

            '''
            # [Test For Check Only Call]
            #self.run_sub_test(sub_name='checkOnly call Test', test_method=self.test_check_only_call)
            is_support = self.run_sub_test(sub_name='checkOnly call Test', test_method=self.test_check_only_call)
            if not is_support:
                self.log.warning('Since video/transcoding not supported, do the next case...')
                self.log.warning('{} is PASS'.format(self.global_dict['test_info']['case_name']))
                continue
            '''

            # [Test For Video Transcoding]
            self.run_sub_test(sub_name='To H264_720P_MKV', test_method=self.test_media_transcoding)
            
            '''
            # Set transcoding setting
            if self.uut['model'] in ['yodaplus']:
                rest_d = self.global_dict['test_info']['rest_info']['video']['duration']
                self.global_dict['transcoding_setting'] = TranscodingSettingInformation('h264', 'mpegTS', '360p', 5*60*1000 if rest_d >= 5*60 else int(rest_d)*1000)
            else:
                self.global_dict['transcoding_setting'] = TranscodingSettingInformation('h264', 'mpegTS', '360p', self.duration)

            # [Test For HLS playlist]
            self.run_sub_test(sub_name='HLS Playlist Test', test_method=self.test_video_playlist)

            # [Test For Video Segment]
            self.run_sub_test(sub_name='Video Segment Test', test_method=self.test_video_segment)
            '''

    # remove sub test
    def test_media_transcoding(self):
        self.global_dict['export_to_csv'] = True
        super(MediaSanityTest, self).test_media_transcoding(test_info=self.global_dict['test_info'])
        self.global_dict['export_to_csv'] = False


    def reboot(self):
        self.timeout = 60*20
        self.log.info('Use SSH command to reboot device.')
        self.ssh_client.reboot_device()
        self.log.info('Expect device reboot complete in {} seconds.'.format(self.timeout))

        start_time = time.time()
        if not self.ssh_client.wait_for_device_to_shutdown(timeout=self.timeout):
            raise self.err.TestFailure('Device was not shut down successfully!')

        time.sleep(10)
        self.utils.update_ip_to_utils(self.wait_for_ip(self.mac))

        if not self.ssh_client.wait_for_device_boot_completed(timeout=self.timeout):
            raise self.err.TestFailure('Device was not boot up successfully!')
        self.log.warning("Reboot complete in {} seconds".format(time.time() - start_time))

        self.ssh_client.check_restsdk_service()
        self.uut_owner.wait_until_cloud_connected(timeout=60*3)

    def wait_for_ip(self, mac, delay=10, max_retry=6*30):
        return retry(
            func=self.get_ip, mac=mac,
            excepts=(Exception), retry_lambda=lambda x: not x or not check_port_pingable(x, self.ssh_client.port),
            delay=delay, max_retry=max_retry, log=self.log.warning
        )

    def get_ip(self, mac):
        self.log.info('Get IP by mac')
        for row in requests.get('http://10.92.235.136').content.split('\n'):
            if mac in row:
                return row.split(' => ')[0]


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
    parser.add_argument('-m', '--mac', help='Device MAC for getting IP after reboot', metavar='MAC')
    parser.add_argument('-trt', '--transcoding_request_timeout', help='Transcoding request timeout', type=int, metavar='SECS', default=60*5)

    test = KDPMediaSanityTest(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
