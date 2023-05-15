# -*- coding: utf-8 -*-
""" Video transcoding test (KAM-22059).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import csv
import sys
from pprint import pformat
# platform modules
from middleware.arguments import GodzillaIntegrationTestArgument
from middleware.godzilla_integration_test import GodzillaIntegrationTest
from platform_libraries.test_result import ELKTestResult
from platform_libraries.pyutils import ignore_unknown_codec
# Sub-tests
from restsdk_tests.functional_tests.get_video_stream import GetVideoStreamTest
from restsdk_tests.functional_tests.upload_file import UploadFileTest
# 3rd party modules
import requests


class VideoTranscoding(GodzillaIntegrationTest):

    TEST_SUITE = 'Video_Transcoding'
    TEST_NAME = 'Video_Transcoding'

    PROJECT = 'godzilla'
    TEST_TYPE = 'functional'
    PRIORITY = 'blocker'
    COMPONENT = 'PLATFORM'
    REPORT_NAME = 'SANITY'

    def init(self):
        # Overwrite this method to print custom message.
        self.integration.summarize = self.summarize
        self.err_during_walk = False

    def test(self):
        # Walk user root from top to bottom.
        for idx, item in enumerate(self.walk_on_nas(), start=1):
            export_file_info = None
            try:
                self.log.info('#'*75)
                # Gen sub-test name
                subtest_name = '{}#{}'.format(idx, ignore_unknown_codec(item['name']))
                self.log.info("Processing file #{}... fileSearch API response: \n{}".format(idx, pformat(item)))
                export_file_info = {'case_name': subtest_name, 'before': item, 'after': None}

                # Check REST SDK return data
                if not self.is_video(item):
                    self.log.info("=> Skip this file which REST SDK doesn't return video information.")
                    self.append_result(subtest_name,
                        # [0] means skip_type=0
                        skipped_message="[STATUS-0] REST SDK doesn't return video information.\nfilesSearch API:{}".format(str(item)),
                        skip_type=0
                    )
                    self.log.info('#'*75)
                    continue

                # Custom settings according by source file.
                container, video_format, content_type = self.get_container_settings(item)

                # Check video is not support or not with check_only flag.
                try:
                    response = self.uut_owner.get_video_stream(
                        file_id=item['id'], container=container, resolution='original', video_codec='h264', duration='5000',
                        check_only=True
                    )
                except requests.HTTPError, e:
                    self.log.info("=> Skip this file because it not support transcode")
                    self.append_result(subtest_name,
                        # [1] means skip_type=1
                        skipped_message="[STATUS-1] Transcoding API doesn't support.\nfilesSearch API:{}{}".format(
                            str(item), "\nRequest URL:{}".format(
                                self.uut_owner.previous_response.request.url) if isinstance(self.uut_owner.previous_response,
                                requests.Response) else ''),
                        skip_type=1
                    )
                    self.log.info('#'*75)
                    continue

                # Start transcoding
                test_pass = self.run_subtest(idx, GetVideoStreamTest, {
                    'file_id': item['id'], 'TEST_NAME': subtest_name,
                    'video_codec': 'h264', 'video_format': container, 'resolution': 'original',
                    'expect_content_type': content_type, 'expect_video_codec': 'h264', 'expect_video_format': video_format,
                    'expect_video_width': item['video'].get('width'), 'expect_video_height': item['video'].get('height'),
                    'quick_test': True, 'request_timeout': 90, 'recorder_dict': export_file_info
                })
            except Exception, e:
                # Be careful think about the behavior of sub-test which also will create a result.
                self.log.exception(str(e))
                self.append_result(subtest_name, error_message=str(e))
            finally:
                if not export_file_info:
                    return
                self.export_to_csv(info=export_file_info, file_name=self.env.output_folder+'/video_info.csv')

    def summarize(self):
        """ Print summarize report. """
        error_tests = []
        failed_tests = []
        skipped_tests = []
        skipped_tests_restsdk = []
        skipped_tests_transcode = []

        # Collect failed sub-tests
        for tr in self.data.test_result:
            if 'error_message' in tr:
                error_tests.append(tr)
            elif 'failure_message' in tr:
                failed_tests.append(tr)
            elif 'skipped_message' in tr:
                skipped_tests.append(tr)
                skip_type = tr.get('skip_type')
                if skip_type == 0:
                    skipped_tests_restsdk.append(tr)
                elif skip_type == 1:
                    skipped_tests_transcode.append(tr)

        # Print message.
        self.log.info('-'*75)
        self.log.info('Total tests : {}'.format(len(self.data.test_result)))
        self.log.info('Error tests: {}'.format(len(error_tests)))
        self.log.info('Failed tests: {}'.format(len(failed_tests)))
        self.log.info('Skipped tests: {}'.format(len(skipped_tests)))
        self.log.info(" - Skipped by REST SDK: {}".format(len(skipped_tests_restsdk)))
        self.log.info(" - Skipped by Transcoding API: {}".format(len(skipped_tests_transcode)))
        self.log.info('')
        for error_test in error_tests:
            self.log.info("=> {} is ERROR".format(error_test['testName']))
        for failed_test in failed_tests:
            self.log.info("=> {} is FAILED".format(failed_test['testName']))
        for skipped_test in skipped_tests_restsdk:
            self.log.info("=> {} is SKIPPED by REST SDK".format(skipped_test['testName']))
        for skipped_test in skipped_tests_transcode:
            self.log.info("=> {} is SKIPPED by Transcoding API".format(skipped_test['testName']))
        self.log.info('-'*75)

        if self.err_during_walk or error_tests or failed_tests:
            return False
        return True

    def run_subtest(self, idx, testcase, custom_env=None):
        """ Custom method to run sub test. """
        subtest = self.integration.gen_subtest(testcase, custom_env)
        self.integration.testcases.append(subtest)
        self.integration.init_subtest(subtest)
        self.integration.reder_subtest(subtest, idx)
        return subtest.launch(callback=self.data.append_subtest)

    def walk_on_nas(self):
        """ Walk user root on remote NAS. """
        # Walk root parent.
        try:
            file_list, sub_folder_list = self.uut_owner.walk_folder(search_parent_id='root', item_parser=None)
            for file in file_list:
                yield file

            # Walk sub-folders from top to bottom.
            while sub_folder_list:
                next_roud_list = []
                for folder_item in sub_folder_list:
                    file_list, sub_folder_list = self.uut_owner.walk_folder(search_parent_id=folder_item['id'], item_parser=None)
                    for file in file_list:
                        yield file
                    next_roud_list+=sub_folder_list # Collect deeper level sub-folders.
                sub_folder_list = next_roud_list
        except Exception, e:
            self.err_during_walk = True
            self.log.exception('Error encountered during walk on nas. Error Message: {}'.format(e))
            raise StopIteration()

    def is_video(self, item):
        """ Check the given item is video or not. """
        if 'video' in item: # Check with 'video' field.
            return True
        return False

    def get_container_settings(self, item):
        return 'fmp4', 'MPEG-4', 'video/mp4'

    def append_result(self, subtest_name, failure_message=None, error_message=None, skipped_message=None, skip_type=None):
        test_result = ELKTestResult(
            test_suite=self.TEST_SUITE, test_name=subtest_name,
            build=self.env.UUT_firmware_version, iteration=self.env.iteration
        )
        if failure_message: test_result['failure_message'] = failure_message
        if error_message: test_result['error_message'] = error_message
        if skipped_message: test_result['skipped_message'] = skipped_message
        if skip_type is not None: test_result['skip_type'] = skip_type
        test_result.summarize(print_out=True)
        self.data.test_result.append(test_result)
        return test_result

    def export_to_csv(self, info, file_name, field_names=['case_name', 'before', 'after']):
        try:
            self.log.debug('Export video inforamtion to csv...')
            with open(file_name, 'a') as csvfile:
                writer = csv.DictWriter(csvfile, field_names)
                writer.writerow(info)
        except Exception, e:
            self.log.exception('Export data failed: {}'.format(e))


if __name__ == '__main__':
    parser = GodzillaIntegrationTestArgument("""\
        *** Video_Transcoding on Kamino Android ***
        Examples: ./run.sh restsdk_tests/integration_tests/video_transcoding.py --uut_ip 10.136.137.159\
        """)

    test = VideoTranscoding(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
