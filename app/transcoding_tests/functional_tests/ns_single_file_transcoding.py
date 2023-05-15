# -*- coding: utf-8 -*-
""" Negative Single File Transcoding Test.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import sys
from pprint import pformat
# 3rd modules
import requests
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
# test modules
from transcoding_tests.lib.converter import TranscodingSettingInformation
# tests
from transcoding_tests.integration_tests.media_sanity import MediaSanityTest


#
# Test Implements
#
class NSSingleFileTranscodingTest(MediaSanityTest):

    TEST_SUITE = 'RESTSDK Transcoding'
    TEST_NAME = 'Negative: Single File Transcoding Test'
    # Popcorn
    TEST_JIRA_ID = 'KAM-17412'


    def init(self):
        super(MediaSanityTest, self).init()
        # Set upload path for uploading.
        if not self.local_data_path:
            self.local_data_path = 'UPLOAD_VIDEOS'
        # Clear old video data.
        self.adb.executeCommand(cmd='rm -r "{}"'.format(self.local_data_path), consoleOutput=True, timeout=60*5)
        # Dowload test video.
        self.adb.executeCommand(cmd='wget "{}" -P "{}" --no-verbose'.format(self.test_file_url, self.local_data_path), consoleOutput=True, timeout=60*30)

    def test(self):
        #TODO: Not handle nothing match at walk_on_nas.
        # Walk user root from top to bottom.
        for retval in self.walk_on_nas():
            # Update test_info.
            test_info = self.gen_test_info(rest_item=retval)
            if not test_info:
                continue

            # Data comaprsion.
            self.file_comaprsion(test_info)

            # Set transcoding setting
            test_info.update(**{
                'case_name': self.TEST_NAME,
                'ts_info': TranscodingSettingInformation('h264', self.target_container, self.target_resolution, self.duration),
                'test_result': self.data.test_result
            })

            # [Test For Negative Video Transcoding]
            try:
                super(MediaSanityTest, self).test_media_transcoding(test_info=test_info)
            except requests.HTTPError, e:
                if '500 Server Error' in str(e): # TOSO: Cannot get reponse ibject??
                    self.log.info('Verify status code: PASSED.')
                    return
            raise self.err.TestFailure('Response status code is incorrect.')

    def after_test(self):
        super(MediaSanityTest, self).after_test()
        # Set test log name.
        self.env.logcat_name = '{}-logcat'.format(self.TEST_NAME)

    #
    # Convert integration test to test case.
    #
    def _run_test(self):
        return TestCase._run_test(self)

    def main(self):
        return TestCase.main(self)

    class Environment(TestCase.Environment):
        pass


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** NSSingleFileTranscodingTest on Kamino Android ***
        Examples: ./run.sh transcoding_tests/functional_tests/ns_single_file_transcoding.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-db_path', '--db_file_path', help='Path of db file', metavar='PATH')
    parser.add_argument('-db_url', '--db_file_url', help='URL of db file to download from file server', metavar='URL')
    parser.add_argument('-duration', '--duration', help='Duration value to convent all test video', type=int, metavar='DURATION', default=None)
    parser.add_argument('-nid', '--not_init_data', help='Use existing data for test', action='store_true', default=False)
    parser.add_argument('-nell', '--not_export_logcat_log', help="Don't export logcat logs at end of each sub-test", action='store_true', default=False)
    parser.add_argument('-nuel', '--not_upload_end_log', help="Don't upload logs to sumologic at end of each sub-test", action='store_true', default=False)
    parser.add_argument('-csf', '--case_start_from', help="Sub-case number start from", type=int, metavar='NUMBER', default=0)
    parser.add_argument('-ldp', '--local_data_path', help="Upload test video from local path via RestSDK call")
    parser.add_argument('-dcur', '--disable_clean_user_root', action='store_true', help="clean user root before uploading video to DUT")  ## This is used by restsdk_transcoding.py 
    parser.add_argument('-rizf', '--reboot_if_zombie_found', help="Reboot device when zombie process found", action='store_false', default=True)
    # For Single File Transcoding Test
    parser.add_argument('-tfu', '--test_file_url', help="Test file URL to download", metavar='URL')
    parser.add_argument('-tc', '--target_container', help="Target container to transcode", metavar='container')
    parser.add_argument('-tr', '--target_resolution', help="Target resolution to transcode", metavar='resolution')

    test = NSSingleFileTranscodingTest(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
