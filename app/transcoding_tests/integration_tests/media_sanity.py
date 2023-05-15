# -*- coding: utf-8 -*-
""" Media Sanity Test (KAM200-897).
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
from middleware.arguments import IntegrationTestArgument
from platform_libraries.compare import local_md5sum, md5sum
from platform_libraries.constants import Kamino
from platform_libraries.popcorn import PopcornTest
from platform_libraries.pyutils import ignore_unknown_codec, retry, save_to_file
# test modules
from transcoding_tests.lib.converter import (
    FileAPIResponseConverter, FFmpegInfoConverter, TranscodingSettingInformation
)
from transcoding_tests.lib.transcoding_settings import API_TRANSCODING_SETTINGS, get_pretranscoding_resolution
# tests
from restsdk_tests.functional_tests.get_video_playlist import GetVideoPlaylistTest
from restsdk_transcoding import add_errmsg_header, RESTSDKTranscoding
# 3rd party modules
import requests


#
# Decorator Tools
#
def sub_test_handler(init_list=False):
    """ For control test flow.
    """
    def wrapper(mothed):
        init = init_list
        def handler(*args, **kwargs):
            self = args[0]
            # Init sub_test_results.
            if init:
                self.global_dict['sub_test_results'] = []
            # Rename for local code.
            rl = self.global_dict['sub_test_results']
            sub_test_index = len(rl)
            # Set default value.
            rl.append(None)
            # Check previous test results.
            if sub_test_index > 0 and rl[0] is None:
                raise self.err.TestSkipped('Video Extraction Test is not PASS')
            elif sub_test_index > 1 and rl[1] is False:
                raise self.err.TestSkipped('The checkOnly call return not support')
            elif sub_test_index > 1 and rl[1] is None:
                raise self.err.TestSkipped('The checkOnly Call Test is not PASS')
            elif sub_test_index > 3 and rl[3] is None:
                raise self.err.TestSkipped('Video Playlist Test is not PASS')
            # Run test
            ret = mothed(*args, **kwargs)
            # Set test result for test flow.
            rl[sub_test_index] = True if ret is None else ret
            return ret
        return handler
    return wrapper


#
# Test Implements
#
class MediaSanityTest(RESTSDKTranscoding, GetVideoPlaylistTest):

    TEST_SUITE = 'RESTSDK Transcoding'
    TEST_NAME = 'Media Sanity Test'
    REPORT_NAME = 'Sanity'

    COMPONENT = 'PLATFORM'
    TEST_JIRA_ID_MAPPING = {
        "1080P_H264_AAC_30FPS.mkv: Video Extraction Test": "KAM-35620",
        "1080P_H264_AAC_30FPS.mkv: checkOnly call Test": "KAM-35622",
        "1080P_H264_AAC_30FPS.mkv: MKV Transcoding Test": "KAM-35621",
        "1080P_H264_AAC_30FPS.mkv: HLS Playlist Test": "KAM-35623",
        "1080P_H264_AAC_30FPS.mkv: Video Segment Test": "KAM-35624",
        "IPHONE_6_MPEG-4_AVC_HIGH@L4.2_AAC__LC_1920X1080_60FPS.MOV: Video Extraction Test": "KAM-35629",
        "IPHONE_6_MPEG-4_AVC_HIGH@L4.2_AAC__LC_1920X1080_60FPS.MOV: checkOnly call Test": "KAM-35627",
        "IPHONE_6_MPEG-4_AVC_HIGH@L4.2_AAC__LC_1920X1080_60FPS.MOV: MKV Transcoding Test": "KAM-35628",
        "IPHONE_6_MPEG-4_AVC_HIGH@L4.2_AAC__LC_1920X1080_60FPS.MOV: HLS Playlist Test": "KAM-35626",
        "IPHONE_6_MPEG-4_AVC_HIGH@L4.2_AAC__LC_1920X1080_60FPS.MOV: Video Segment Test": "KAM-35625",
        "IPHONE_7_PLUS_MPEG-4_AVC_HIGH@L3.1_AAC__LC_1280X720_30FPS.MOV: Video Extraction Test": "KAM-35634",
        "IPHONE_7_PLUS_MPEG-4_AVC_HIGH@L3.1_AAC__LC_1280X720_30FPS.MOV: checkOnly call Test": "KAM-35632",
        "IPHONE_7_PLUS_MPEG-4_AVC_HIGH@L3.1_AAC__LC_1280X720_30FPS.MOV: MKV Transcoding Test": "KAM-35633",
        "IPHONE_7_PLUS_MPEG-4_AVC_HIGH@L3.1_AAC__LC_1280X720_30FPS.MOV: HLS Playlist Test": "KAM-35631",
        "IPHONE_7_PLUS_MPEG-4_AVC_HIGH@L3.1_AAC__LC_1280X720_30FPS.MOV: Video Segment Test": "KAM-35630",
        "IPHONE_8_PLUS_MPEG-4_HEVC_Main@L5@Main_AAC__LC_3840X2160_30FPS.MOV: Video Extraction Test": "KAM-35639",
        "IPHONE_8_PLUS_MPEG-4_HEVC_Main@L5@Main_AAC__LC_3840X2160_30FPS.MOV: checkOnly call Test": "KAM-35637",
        "IPHONE_8_PLUS_MPEG-4_HEVC_Main@L5@Main_AAC__LC_3840X2160_30FPS.MOV: MKV Transcoding Test": "KAM-35638",
        "IPHONE_8_PLUS_MPEG-4_HEVC_Main@L5@Main_AAC__LC_3840X2160_30FPS.MOV: HLS Playlist Test": "KAM-35636",
        "IPHONE_8_PLUS_MPEG-4_HEVC_Main@L5@Main_AAC__LC_3840X2160_30FPS.MOV: Video Segment Test": "KAM-35635",
        "Pixel_2_MPEG-4_AVC_high@L4.1_AAC__LC_1920X1080_30FPS.mp4: Video Extraction Test": "KAM-35644",
        "Pixel_2_MPEG-4_AVC_high@L4.1_AAC__LC_1920X1080_30FPS.mp4: checkOnly call Test": "KAM-35642",
        "Pixel_2_MPEG-4_AVC_high@L4.1_AAC__LC_1920X1080_30FPS.mp4: MKV Transcoding Test": "KAM-35643",
        "Pixel_2_MPEG-4_AVC_high@L4.1_AAC__LC_1920X1080_30FPS.mp4: HLS Playlist Test": "KAM-35641",
        "Pixel_2_MPEG-4_AVC_high@L4.1_AAC__LC_1920X1080_30FPS.mp4: Video Segment Test": "KAM-35640",
        "The Backwater Gospel.mp4: Video Extraction Test": "KAM-35649",
        "The Backwater Gospel.mp4: checkOnly call Test": "KAM-35647",
        "The Backwater Gospel.mp4: MKV Transcoding Test": "KAM-35648",
        "The Backwater Gospel.mp4: HLS Playlist Test": "KAM-35646",
        "The Backwater Gospel.mp4: Video Segment Test": "KAM-35645",
        '''The Backwater Gospel~!@#$%^&()_+`-=[]{};',..mp4: Video Extraction Test''': "KAM-36065",
        '''The Backwater Gospel~!@#$%^&()_+`-=[]{};',..mp4: checkOnly call Test''': "KAM-36066",
        '''The Backwater Gospel~!@#$%^&()_+`-=[]{};',..mp4: MKV Transcoding Test''': "KAM-36067",
        '''The Backwater Gospel~!@#$%^&()_+`-=[]{};',..mp4: HLS Playlist Test''': "KAM-36068",
        '''The Backwater Gospel~!@#$%^&()_+`-=[]{};',..mp4: Video Segment Test''': "KAM-36069"
    }
    ISSUE_JIRA_ID_MAPPING = {
    }


    def declare(self):
        super(MediaSanityTest, self).declare()
        self.duration = None
        self.transcoding_request_timeout = 60*5

    def test(self):
        # Additional logs for KAM200-1778.
        self.adb.executeShellCommand(cmd='getprop | grep rtk.ffmpeg.enable_stream_check', consoleOutput=True)

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
            self.run_sub_test(sub_name='Video Extraction Test', test_method=self.test_extraction)

            # Set transcoding setting
            self.global_dict['transcoding_setting'] = TranscodingSettingInformation('h264', 'matroska', '360p', self.duration)

            # [Test For Check Only Call]
            self.run_sub_test(sub_name='checkOnly call Test', test_method=self.test_check_only_call)

            # [Test For Video Transcoding]
            self.run_sub_test(sub_name='MKV Transcoding Test', test_method=self.test_media_transcoding)

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


    def gen_test_info(self, rest_item):
        # Separate return data.
        file_path, rest_resp = rest_item # unicode data.
        # Init task information.
        info = self.gen_task_info({
            'file_path': file_path,
            'rest_resp': rest_resp, 
            'prepared_raw': self.get_prepared_video(file_path=file_path), # Raw data form prepared DB.
        })
        # Skip the file which doesn't found in database.
        if not info['prepared_raw']:
            self.log.debug("Skip it! This file isn't in expect data set or local extraction failed. fileSearch API response: \n{}".format(pformat(rest_resp)))
            return None

        # Convert raw data to dict data.
        info['rest_info'] = FileAPIResponseConverter(info['rest_resp'], logging=self.log).convert()
        info['prepared_info'] = FFmpegInfoConverter(info['prepared_raw'], logging=self.log).convert()
        # Gernate rotated video data.
        self.gen_rotate_video(test_info=info)
        return info

    def run_sub_test(self, sub_name, test_method, args_dict={}):
        """ A method to run a function as sub test. 
        TODO: Add this feature to middleware.
        """
        # Increase sub-task number.
        self.global_dict['task_idx'] += 1

        # Rename for local code.
        task_idx, info, ts, export_to_csv, _ = self.global_dict.values()

        # Reset task inforamtion.
        info.update(**{
            'index': task_idx,
            'case_name': '{}# {}: {}'.format(task_idx, ignore_unknown_codec(info['rest_info']['name']), sub_name),
            'ts_info': ts,
            'test_result': {}
        })
        # Skip case if a case number is specified.
        if self.case_start_from and self.case_start_from > task_idx:
            self.log.warning('{} is SKIPPED'.format(info['case_name']))
            return

        try:
            self.log.info('#'*75)
            self.uut.adb_log('*** Start Sub-test #{} ({})...'.format(task_idx, info['case_name']))
            info['test_result']['start_time'] = time.time()
            ret = test_method(**args_dict)
            self.log.warning('{} is PASS'.format(info['case_name']))
            return ret
        except self.err.TestSkipped, e:
            self.log.exception(str(e))
            self.log.warning('{} is SKIPPED'.format(info['case_name']))
            info['test_result']['skipped_message'] = str(e)
        except Exception, e:
            self.log.exception(str(e))
            self.log.warning('{} is FAILED'.format(info['case_name']))
            info['test_result']['failure_message'] = str(e)
        finally:
            info['test_result']['end_time'] = time.time()

            # Save test result.
            test_result = self.append_result(info['case_name'], 
                failure_message=info['test_result']['failure_message'] if 'failure_message' in info['test_result'] else None,
                skipped_message=info['test_result']['skipped_message'] if 'skipped_message' in info['test_result'] else None
            )

            # popcorn support
            if not self.env.disable_popcorn_report:
                self.gen_popcorn_test(test_result, info)

            # Export video inforamtion during test.
            if export_to_csv:
                self.export_to_csv(info={
                    'case_name': info['case_name'], 'before': info['prepared_raw'], 'rest': info['rest_resp'], 'after': info['converted_info']
                }, file_name=self.env.output_folder+'/video_info.csv', field_names=['case_name', 'before', 'rest', 'after'])

            self.uut.adb_log('*** Sub-test #{} Is Done'.format(task_idx))
            self.done_log(logcat_name='{}-logcat'.format(info['case_name']))
            self.log.info('#'*75)

    def gen_popcorn_test(self, ELK_test_result, test_info):
        # set result
        if 'skipped_message' in test_info['test_result']:
            result = 'SKIPPED'
            error_msg = test_info['test_result']['skipped_message']
        elif 'failure_message' in test_info['test_result']:
            result = 'FAILED'
            error_msg = test_info['test_result']['failure_message']
        else:
            result = 'PASSED'
            error_msg = ''

        # Covert time
        S_TIME = int(round(test_info['test_result']['start_time'] * 1000))
        E_TIME = int(round(test_info['test_result']['end_time'] * 1000))

        # Map jira id by name
        jira_id = ''
        for key in self.TEST_JIRA_ID_MAPPING.keys():
            if key in test_info['case_name']:
                jira_id = self.TEST_JIRA_ID_MAPPING[key]
        issue_jira_id = ''
        for key in self.ISSUE_JIRA_ID_MAPPING.keys():
            if key in test_info['case_name']:
                issue_jira_id = self.ISSUE_JIRA_ID_MAPPING[key]

        # gen popcorn object
        ELK_test_result.POPCORN_RESULT = PopcornTest(
            name=test_info['case_name'], test_id=jira_id, result=result,
            component=self.COMPONENT, jira_issue_key=issue_jira_id,
            error=error_msg, start=S_TIME, end=E_TIME
        )

        # Update time.
        ELK_test_result.POPCORN_RESULT.TEST_START_TIME = S_TIME
        ELK_test_result.POPCORN_RESULT.TEST_END_TIME = E_TIME

    #
    # Test For Media Transcoding
    #
    def file_comaprsion(self, test_info):
        self.uut.adb_log('*** Start Data Comaprsion...'.format(test_info['index']))

        self.file_id = test_info['rest_resp']['id']
        # Get file
        content = self.uut_owner.get_file_content_v3(file_id=self.file_id).content
        # Verify MD5sum
        remote_md5 = md5sum(content)
        self.log.info('MD5 of remote file: {}'.format(remote_md5))

        # NOTE: Only first match
        if self.local_data_path: # On local.
            stdout, stderr = self.adb.executeCommand("find . -name '{}' -type f".format(test_info['rest_info']['name']))
        else: # In USB.
            stdout, stderr = self.adb.executeShellCommand("find {} -name '{}' -type f".format(Kamino.MOUNT_PATH, test_info['rest_info']['name']))
        if not stdout:
            raise self.err.TestFailure('Source file: {} not found.'.format(test_info['rest_info']['name']))
        files = stdout.splitlines()
        self.log.info('Source file: {}'.format(files[0]))
        if self.local_data_path: # On local.
            source_md5 = local_md5sum(files[0])
        else: # In USB.
            stdout, stderr = self.adb.executeShellCommand("md5sum '{}'".format(files[0]))
            source_md5 = stdout.split()[0]
        self.log.info('MD5 of source file: {}'.format(source_md5))

        if remote_md5 != source_md5:
            self.log.info('Verify md5sum: FAILED.')
            raise self.err.TestFailure('Content md5sum is incorrect.')
        self.log.info('Verify md5sum: PASSED.')

        self.uut.adb_log('*** Data Comaprsion Is Done'.format(test_info['index']))

    @sub_test_handler(init_list=True)
    def test_extraction(self):
        # Data comaprsion. (enable if we need it)
        #self.file_comaprsion(test_info=self.global_dict['test_info'])
        # Extraction test
        super(MediaSanityTest, self).test_extraction(test_info=self.global_dict['test_info'])

    @sub_test_handler()
    def test_check_only_call(self):
        return super(MediaSanityTest, self).test_check_only_call(test_info=self.global_dict['test_info'])

    @sub_test_handler()
    def test_media_transcoding(self):
        self.global_dict['export_to_csv'] = True
        super(MediaSanityTest, self).test_media_transcoding(test_info=self.global_dict['test_info'])
        self.global_dict['export_to_csv'] = False

    @sub_test_handler()
    def test_video_playlist(self):
        return self._test_video_playlist(test_info=self.global_dict['test_info'])

    def _test_video_playlist(self, test_info):
        self.uut.adb_log('*** Start Video Playlist Test (Sub-test #{})...'.format(test_info['index']))

        playlist_duration = self.duration
        if self.uut['model'] in ['yodaplus']:
            self.log.warning('Wait for pre-transcoding is ready...')
            def pretranscoding_check(resp):
                if not resp or not resp.json().get('optimizedAvailable'):
                    self.log.info('Pre-transcoding is not ready, check background process...')
                    self.adb.is_any_FFmpeg_running() # just to check status again.
                    return True
                return False
            resp = retry( # Retry for 5 mins * 6 files * 2 for buffer.
                func=self.uut_owner.get_video_playlist,
                file_id=test_info['rotated_rest_info']['id'], container=test_info['ts_info']['container'], resolution=test_info['ts_info']['resolution'],
                video_codec=test_info['ts_info']['video']['videoCodec'], check_only=True, duration=self.global_dict['transcoding_setting']['video']['duration']*1000, 
                excepts=(Exception), retry_lambda=pretranscoding_check, delay=5*60*2, max_retry=6, log=self.log.warning
                # delay for 5 mins * 2 for make sure it can done at least one video in each delay.
            )
            self.log.warning('optimizedAvailable: {}'.format(resp.json().get('optimizedAvailable')))
            playlist_duration = self.global_dict['transcoding_setting']['video']['duration']*1000 # 5 mins
        self.log.info('Wait for all the FFmepg process exit before start testing to avoid playlist expire...')
        self.handle_existing_FFmpeg_process()

        response = self.uut_owner.get_video_playlist(
            file_id=test_info['rotated_rest_info']['id'], video_codec=test_info['ts_info']['video']['videoCodec'],
            container=test_info['ts_info']['container'], resolution=test_info['ts_info']['resolution'],
            duration=playlist_duration
        )
        self.log.info('Elapsed Time: {} sec.'.format(response.elapsed.total_seconds()))
        M3U8_content = response.content
        self.log.info('M3U8(Playlist) Content: \n{}'.format(M3U8_content))
        self.verify_M3U8_header(response)
        self.verify_M3U8_content(M3U8_content)
        self.uut.adb_log('*** Video Playlist Test (Sub-test #{}) Is Done'.format(test_info['index']))
        return M3U8_content

    @sub_test_handler()
    def test_video_segment(self):
        #if self.uut['model'] in ['yodaplus']:
            self._test_pretranscoding_with_video_segment(test_info=self.global_dict['test_info'], M3U8_content=self.global_dict['sub_test_results'][3])
        #else:
        #    self._test_video_segment(test_info=self.global_dict['test_info'], M3U8_content=self.global_dict['sub_test_results'][3])

    def _test_pretranscoding_with_video_segment(self, test_info, M3U8_content):
        self.uut.adb_log('*** Start Video Segment Test (Sub-test #{})...'.format(test_info['index']))
        
        # Verify each video link.
        for segment_index, video_link in enumerate(self.split_video_link(M3U8_content), 1):
            try:
                # HLS session expires if it has no request to a sequment over about 20s.
                #self.handle_existing_FFmpeg_process()
                self.log.warning('Verify link of video segment #{}: {}'.format(segment_index, video_link))
                vsir = VideoSequmentInfoReplacement(info_dict=test_info['ts_info'])
                try:
                    def verify_video_segment():
                        try:
                            # HLS session expires if it has no request to a sequment over about 20s.
                            self.handle_existing_FFmpeg_process(timeout=10) # Check for each retry.
                            video_response = self._send_request(file_id=test_info['rotated_rest_info']['id'], video_link=video_link)
                            self.log.info('Elapsed Time: {} sec.'.format(video_response.elapsed.total_seconds()))
                            save_to_file(iter_obj=video_response.iter_content(chunk_size=1024), file_name=self.local_file)
                            # Replace video information by video segment information for verification.
                            test_info['ts_info'] = vsir.replace_by_url(url=video_link)
                            # Per KDP-2368 and change resolution
                            resolution = get_pretranscoding_resolution(video_info=test_info['rotated_prepared_info'])
                            self.log.info('Expect video segment is in {}'.format(resolution))
                            test_info['ts_info'] = vsir.replace_resolution(resolution)
                            self.verify_transcoding_header(video_response, test_info)
                            self.verify_transcoding_content(test_info)
                        except Exception as e:
                            if os.path.exists(self.local_file): # For tracing bug.
                                save_path = os.path.join(self.env.output_folder, uuid4().hex+'.ts')
                                self.log.warning('Move stream file to {} for tracing'.format(save_path))
                                os.rename(self.local_file, save_path)
                            raise
                        finally:
                            if os.path.exists(self.local_file):
                                os.remove(self.local_file)

                    retry( # Retry for tracing issues.
                        func=verify_video_segment,
                        excepts=(Exception), delay=10, max_retry=10, log=self.log.warning
                    )
                finally:
                    # Recover back video information.
                    test_info['ts_info'] = vsir.get_original_dict()
                    self.adb.is_any_FFmpeg_running() # just to check status again.
                    self.log.warning('Verify link of video segment #{} is done'.format(segment_index))
            except Exception as e: # Add Video Segment information to error message.
                try:
                    raise type(e), type(e)('[Video Segment #{}] {}'.format(segment_index, e.message)), sys.exc_info()[2]
                except: # For exceptions which have more than one argiment.
                    raise e

        self.uut.adb_log('*** Start Video Segment Test for (Sub-test #{})...'.format(test_info['index']))

    def _test_video_segment(self, test_info, M3U8_content):
        self.uut.adb_log('*** Start Video Segment Test (Sub-test #{})...'.format(test_info['index']))
        # Verify each video link.
        for segment_index, video_link in enumerate(self.split_video_link(M3U8_content), 1):
            try:
                self.handle_existing_FFmpeg_process()
                rebooted = self.reboot_device_if_zombie_found()
                self.log.warning('Verify link of video segment #{}: {}'.format(segment_index, video_link))

                vsir = VideoSequmentInfoReplacement(info_dict=test_info['ts_info'])
                try:
                    # Do video transcoding (retry 10 times for reboot process).
                    if rebooted: self.log.info('The next RestSDK call could retry 10 times cause it invoked after device rebooted...')
                    video_response = retry(
                        func=self._send_request,
                        file_id=test_info['rotated_rest_info']['id'], video_link=video_link,
                        excepts=(requests.HTTPError, TypeError, AttributeError), delay=10, max_retry=10 if rebooted else 0, log=self.log.warning
                    )
                    self.log.info('Elapsed Time: {} sec.'.format(video_response.elapsed.total_seconds()))
                    save_to_file(iter_obj=video_response.iter_content(chunk_size=1024), file_name=self.local_file)
                    # Replace video information by video segment information for verification.
                    test_info['ts_info'] = vsir.replace_by_url(url=video_link)
                    self.verify_transcoding_header(video_response, test_info)
                    try:
                        self.verify_transcoding_content(test_info)
                    except Exception as check_err:
                        # For Improve Video Start Time(KAM200-2371), the first three segment are 720p.
                        if segment_index > 3:
                            raise
                        self.log.warning('Check this is pre-transcoding segment or not...')
                        resp = self._send_request( # Use checkOnly call.
                            file_id=test_info['rotated_rest_info']['id'], video_link=video_link+'&checkOnly=true'
                        )
                        if not resp or not resp.json().get('optimizedAvailable'):
                            raise self.err.TestFailure(check_err)
                        self.log.warning('It is a pre-transcoding segment and it should be 720p...')
                        test_info['ts_info'] = vsir.replace_resolution(resolution='720p')
                        self.verify_transcoding_content(test_info)
                finally:
                    if os.path.exists(self.local_file):
                        os.remove(self.local_file)
                    # Recover back video information.
                    test_info['ts_info'] = vsir.get_original_dict()
                    self.log.warning('Verify link of video segment #{} is done'.format(segment_index))
            except Exception as e: # Add Video Segment information to error message.
                raise type(e), type(e)('[Video Segment #{}] {}'.format(segment_index, e.message)), sys.exc_info()[2]

        self.uut.adb_log('*** Start Video Segment Test for (Sub-test #{})...'.format(test_info['index']))

    def handle_existing_FFmpeg_process(self, delay=5, timeout=60*70, time_to_kill=60*60):
        super(MediaSanityTest, self).handle_existing_FFmpeg_process(delay, timeout, time_to_kill)

class VideoSequmentInfoReplacement(object):
    """ Utility to change global video information temporally for verify video segment. """

    def __init__(self, info_dict):
        self.src_info = info_dict
        self.rep_info = copy.deepcopy(info_dict)

    def replace(self, replace_dict):
        self.rep_info.update(replace_dict)
        return self.rep_info

    def replace_by_url(self, url):
        args_strings = url.split('?').pop().split('&')
        for args_string in args_strings:
            key, value = args_string.split('=')
            # Change duration.
            if key == 'duration':
                self.rep_info['video']['duration'] = float(value)/1000
        return self.rep_info

    def replace_resolution(self, resolution):
        settings = API_TRANSCODING_SETTINGS[resolution]
        self.rep_info['video']['width'] = settings['width']
        self.rep_info['video']['height'] = settings['height']
        return self.rep_info

    def get_original_dict(self):
        return self.src_info


if __name__ == '__main__':
    parser = IntegrationTestArgument("""\
        *** MediaSanityTest on Kamino Android ***
        Examples: ./run.sh transcoding_tests/integration_tests/media_sanity.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-db_path', '--db_file_path', help='Path of db file', metavar='PATH')
    parser.add_argument('-db_url', '--db_file_url', help='URL of db file to download from file server', metavar='URL')
    parser.add_argument('-duration', '--duration', help='Duration value to convent all test video', type=int, metavar='DURATION', default=None)
    parser.add_argument('-nid', '--not_init_data', help='Use existing data for test', action='store_true', default=False)
    parser.add_argument('-nell', '--not_export_logcat_log', help="Don't export logcat logs at end of each sub-test", action='store_true', default=False)
    parser.add_argument('-nuel', '--not_upload_end_log', help="Don't upload logs to sumologic at end of each sub-test", action='store_true', default=False)
    parser.add_argument('-csf', '--case_start_from', help="Sub-case number start from", type=int, metavar='NUMBER', default=0)
    parser.add_argument('-ldp', '--local_data_path', help="Upload test video from local path via RestSDK call")
    parser.add_argument('-rizf', '--reboot_if_zombie_found', help="Reboot device when zombie process found", action='store_false', default=True)

    test = MediaSanityTest(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
