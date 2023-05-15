# -*- coding: utf-8 -*-
""" Video transcoding test (KAM111-214).
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import copy
import json
import os
import sys
import time
from pprint import pformat
from uuid import uuid4
# platform modules
from middleware.arguments import IntegrationTestArgument
from middleware.decorator import exit_test
from platform_libraries.pyutils import ignore_unknown_codec, retry, save_to_file
from platform_libraries.sql_client import SQLite
# test modules
from transcoding_tests.lib.comparator import Comparator, ErrValueNotFound, SPECLimitationChecker
from transcoding_tests.lib.converter import (
    FileAPIResponseConverter, FFmpegInfoConverter, TranscodingSettingInformation,
    VideoConverter, SPECLimitationInformation
)
from transcoding_tests.lib.transcoding_settings import (
    API_CONTAINERS, API_VIDEO_CODECS, API_MIMETYPE, API_TRANSCODING_SETTINGS, get_max_api_resolution_options,
    Monarch_Transcoding_Rules, Pelican_Transcoding_Rules, YodaPlus_Transcoding_Rules
)
# integration tests
from restsdk_tests.integration_tests.video_transcoding import VideoTranscoding
# 3rd party modules
import requests


#
# Decorator Tools
#
def add_errmsg_header(errmsg_header):
    def wrapper(mothed):
        prefix_msg = errmsg_header
        def errmsg_adder(*args, **kwargs):
            try:
                return mothed(*args, **kwargs)
            except Exception as e:
                raise type(e), type(e)('{} {}'.format(prefix_msg, e.message)), sys.exc_info()[2]
        return errmsg_adder
    return wrapper


#
# Test Implements
#
class RESTSDKTranscoding(VideoTranscoding):

    TEST_SUITE = 'RESTSDK_Transcoding'
    TEST_NAME = 'RESTSDK_Transcoding'

    def declare(self):
        # Default values
        self.db_file_path = None
        self.duration = 5000
        self.not_init_data = False
        self.not_export_logcat_log = False
        self.not_upload_end_log = False
        self.case_start_from = 0
        self.test_only_240p = False
        # Test data path for uploading.
        self.local_data_path = None
        self.disable_clean_user_root = False
        # Vars for hot fix.
        self.reboot_if_zombie_found = True
        # Vars for test.
        self.local_file = 'tmp_transcoded_content'
        self.transcoding_request_timeout = 15

        # Vars for trancoding.
        self.duration = 5000

    def init(self):
        # Overwrite this method to print custom message.
        if hasattr(self, 'integration'): self.integration.summarize = self.summarize
        self.err_during_walk = False
        # Handle parameters.
        if self.db_file_path:
            self.db_file = self.db_file_path
        elif self.db_file_url: 
            # Download prepared DB file, and create connection.
            self.adb.executeCommand(cmd='wget "{}"'.format(self.db_file_url), consoleOutput=True, timeout=60*30)
            self.db_file = self.db_file_url.rsplit('/', 1).pop()
        else:
            raise self.err.StopTest('Need db_file_path or db_file_url')
        if not os.path.exists(self.db_file):
            raise self.err.StopTest('Database not found')
        #self.db_client = SQLite(db_file=self.db_file)

    def before_test(self):
        """ Prepare test environment. """
        if self.not_init_data:
            return

        if not getattr(self, 'disable_clean_user_root', False):
            self.log.info("Clean UUT owner's home directory...")
            self.uut_owner.clean_user_root()
        else:
            if self.local_data_path:
                try:
                    folder_id = self.uut_owner.get_data_id_list(type='folder', parent_id='root', data_name=self.local_data_path)
                    self.log.info("Delete '{}' in UUT owner's home directory...".format(self.local_data_path))
                    if folder_id:
                        self.uut_owner.clean_user_root(id_list=[folder_id])
                    else:
                        pass
                # If folder "self.local_data_path" is not created yet, there will be RuntimeError: Cannot find specified folder.
                # It is OK.
                except:
                    pass

        if self.local_data_path: # Copy test data by uploading via RestSDK API.
            self.log.info("Upload test data from local to UUT owner's home directory...")
            self.uut_owner.recursive_upload(path=self.local_data_path)
            self.log.info("Uploading is done.")
        else: # Copy test data by USB slurp.
            self.log.info("Copy test data from USB to UUT owner's home directory...")
            copy_task_id, usb_info, resp = self.uut_owner.usb_slurp(timeout=60*60*12)
            self.log.info("USB Slurp is done.")

        # Since we use USB slurp, has no good idea to make sure all pre-transdonig is done, just wait for it more times.
        self.log.info('Wait for all the FFmepg process exit before start to run test...')
        for idx, _ in enumerate(self.walk_on_nas(), 1): # Wait for the same number as copied files. 
            time.sleep(5)
            self.log.info('Waiting #{}...'.format(idx))
            try:
                self.handle_existing_FFmpeg_process(timeout=60*10, time_to_kill=60*11) # Max 10 min for each file.
            except:
                pass

    def after_test(self):
        # Set main test log name.
        self.env.logcat_name = 'RESTSDK_Transcoding-logcat'
        # Clean DB file.
        if self.db_file_url and os.path.exists(self.db_file):
            os.remove(self.db_file)

    def get_prepared_video(self, file_path):
        # FIXME: If it has performance issue on creating connection for each reuqest.
        with SQLite(db_file=self.db_file) as self.db_client:
            # Generate SQL command: Search by full match path and video only.
            sql = u"""
                SELECT *, COUNT(*) as total
                FROM   mediainfo
                WHERE  path == "{}" AND 
                       mediainfo LIKE "%codec_type"": ""video""%";
            """.format(file_path)
            self.log.debug(u"SQL: {}".format(sql))
            # Send request
            cur = self.db_client.cursor.execute(sql)
            row = cur.fetchone()
            self.log.debug("rowcount: {}".format(row['total']))
            if not row['total']:
                self.log.info("Data not found in database.")
                return None
            try:
                return json.loads(row['mediainfo'])
            except:
                self.log.info("Data is not a correct json formation.")
                return None

    def gen_rotate_video(self, test_info):
        """ Rotate video if height is larger than width.
        """
        # TODO: Set "rotate" to 0 after rotated a video if need.
        # Rotate rest_info.
        test_info['rotated_rest_info'] = copy.deepcopy(test_info['rest_info'])
        if self._do_need_rotate_for_direction(info=test_info['rotated_rest_info']):
            self._flip_video(info=test_info['rotated_rest_info'], angle=test_info['rotated_prepared_info']['rotate'])
            self.log.debug('rotated test_info["rotated_rest_info"], switch width and height: \n{}'.format(pformat(test_info['rotated_rest_info'])))

        # Rotate prepared_info.
        test_info['rotated_prepared_info'] = copy.deepcopy(test_info['prepared_info'])
        if self._do_need_rotate_for_direction(info=test_info['rotated_prepared_info']):
            self._flip_video(info=test_info['rotated_prepared_info'], angle=test_info['rotated_prepared_info']['rotate'])
            self.log.debug('rotated test_info["rotated_prepared_info"], switch width and height: \n{}'.format(pformat(test_info['rotated_prepared_info'])))

    def _do_need_rotate_by_metadata(self, info):
            return info['rotate']

    def _rotate_video_by_metadata(self, info, angle):
        # Per Gabriel's resposne in email at 2018/08/19.
        if angle%90:
            self.log.warning("Rotate: {} is not multiple of 90. Not rotate video, please check logic to handle it!".format(angle))
            return
        if angle/90%2:
            self._flip_video(info)

    def _do_need_rotate_for_direction(self, info):
            return info['video']['width'] < info['video']['height']

    def _flip_video(self, info):
        info['video']['width'], info['video']['height'] = (info['video']['height'], info['video']['width'])

    def gen_task_info(self, update_dict=None):
        info = {
            'index': None,
            'case_name': None,
            'file_path': None,
            'rest_resp': None, # API reponse.
            'rest_info': None, # Information data from "rest_resp" data.
            'rotated_rest_info': None, # Rotated "rest_info" data.
            'prepared_raw': None, # Raw data form prepared DB.
            'prepared_info': None, # Information data from "prepared_raw" data.
            'rotated_prepared_info': None, # Rotated "prepared_info" data.
            'converted_info': None,
            'ts_info': None, # Touple data of transcoding setting.
            'test_result': {}
        }
        info.update(**update_dict)
        return info

    def test(self):
        task_idx = 0

        # Walk user root from top to bottom.
        for retval in self.walk_on_nas():
            # Separate return data.
            file_path, rest_resp = retval # unicode data.
            # Init task information.
            info = self.gen_task_info({
                'file_path': file_path,
                'rest_resp': rest_resp, 
                'prepared_raw': self.get_prepared_video(file_path=file_path), # Raw data form prepared DB.
            })
            # Skip the file which doesn't found in database.
            if not info['prepared_raw']:
                self.log.warning("Skip it! This file isn't in expect data set or local extraction failed. fileSearch API response: \n{}".format(pformat(rest_resp)))
                continue

            # Convert raw data to dict data.
            info['rest_info'] = FileAPIResponseConverter(info['rest_resp'], logging=self.log).convert()
            info['prepared_info'] = FFmpegInfoConverter(info['prepared_raw'], logging=self.log).convert()
            # Gernate rotated video data.
            self.gen_rotate_video(test_info=info)

            # Start test
            for ts in self.transcoding_settings(media_info=info['rotated_prepared_info']):
                # Increase sub-task number.
                task_idx += 1
                # Reset task inforamtion.
                info.update(**{
                    'index': task_idx,
                    'case_name': '{}#{}#{}-{}-{}'.format(task_idx, ignore_unknown_codec(info['rest_info']['name']),
                        ts['video']['videoCodec'], ts['container'], ts['resolution']),
                    'ts_info': ts,
                    'test_result': {}
                })
                # Skip case if a case number is specified.
                if self.case_start_from and self.case_start_from > task_idx:
                    self.log.info('SKIP sub-case: {}'.format(info['case_name'])) 
                    continue

                try:
                    self.log.info('#'*75)
                    self.uut.adb_log('*** Start Sub-test #{}...'.format(task_idx))

                    # [Test For REST SDK Extraction]
                    self.test_extraction(test_info=info)

                    # [Test For Check Only Call]
                    is_support = self.test_check_only_call(test_info=info)
                    if not is_support:
                        self.log.warning('Since video/transcoding not supported, do the next case...')
                        self.log.warning('{} is PASS'.format(info['case_name']))
                        continue

                    # [Test For Media Transcoding]
                    self.test_media_transcoding(test_info=info)

                    self.log.warning('{} is PASS'.format(info['case_name']))
                except Exception, e:
                    # Be careful think about the behavior of sub-test which also will create a result.
                    self.log.exception(str(e))
                    self.log.warning('{} is FAILED'.format(info['case_name']))
                    info['test_result']['error_message'] = str(e)
                finally:
                    # Save test result.
                    self.append_result(info['case_name'], **info['test_result'])

                    # Export video inforamtion during test.
                    self.export_to_csv(info={
                        'case_name': info['case_name'], 'before': info['prepared_raw'], 'rest': info['rest_resp'], 'after': info['converted_info']
                    }, file_name=self.env.output_folder+'/video_info.csv', field_names=['case_name', 'before', 'rest', 'after'])

                    self.uut.adb_log('*** Sub-test #{} Is Done'.format(task_idx))
                    self.done_log(logcat_name='{}-logcat'.format(info['case_name']))
                    self.log.info('#'*75)

    def done_log(self, logcat_name):
        """ Export and upload logs. """
        self.env.logcat_name = logcat_name
        if not self.not_export_logcat_log:
            self.data.export_logcat_log()
        if not self.not_upload_end_log:
            self.data.upload_logs_to_sumologic()

    def walk_on_nas(self):
        """ Walk user root on remote NAS. """
        usb_folder_history = {}

        def record_folders(folder_list):
            for item in folder_list:
                usb_folder_history[item['id']] = {
                    'name': item['name'],
                    'parentID':  item['parentID']
                }

        def get_full_path(file):
            paths = []
            parent_id = file['parentID']
            # Since root folder is not in list, since loop will stop when finding root ID.
            while parent_id in usb_folder_history:
                folder = usb_folder_history[parent_id]
                sub_path = folder['name']
                paths.append(sub_path)
                parent_id = folder['parentID']
            self.log.debug('[get_full_path()] Before sorting paths:{}'.format(paths))
            paths.reverse()
            paths.append(file['name'])
            self.log.debug('[get_full_path()] Sorted paths:{}'.format(paths))
            return u'/'.join(paths)

        # Walk root parent or local_data_path if specified.
        try:
            if self.local_data_path:
                folder_id = self.uut_owner.get_data_id_list(type='folder', parent_id='root', data_name=self.local_data_path)
                file_list, sub_folder_list = self.uut_owner.walk_folder(search_parent_id=folder_id, item_parser=None)
            else:
                file_list, sub_folder_list = self.uut_owner.walk_folder(search_parent_id='root', item_parser=None)

            for file in file_list:
                yield get_full_path(file), file

            # Walk sub-folders from top to bottom.
            while sub_folder_list:
                next_roud_list = []
                for folder_item in sub_folder_list:
                    file_list, sub_folder_list = self.uut_owner.walk_folder(search_parent_id=folder_item['id'], item_parser=None)
                    for file in file_list:
                        yield get_full_path(file), file
                    next_roud_list+=sub_folder_list # Collect deeper level sub-folders.
                sub_folder_list = next_roud_list
                record_folders(sub_folder_list) # Start recording at 2 level folder.
        except Exception, e:
            self.err_during_walk = True
            self.log.exception('Error encountered during walk on nas. Error Message: {}'.format(e))
            raise StopIteration()


    #
    # Test For REST SDK Extraction
    #
    @add_errmsg_header(errmsg_header='[STATUS-0]')
    def test_extraction(self, test_info):
        """ Main Logic of test.
        """
        self.uut.adb_log('*** Start Extraction Test (Sub-test #{})...'.format(test_info['index']))
        # Convert all inforamtion to the same data format.
        self.log.debug('API response(rest_resp):\n{}'.format(pformat(test_info['rest_resp'])))
        self.log.debug('prepared_info:\n{}'.format(pformat(test_info['prepared_info'])))

        # Compare values.
        cmpt = Comparator(src_set=test_info['prepared_info'], cmp_set=test_info['rest_info'], logging=self.log)
        for cmp_method in ['cmp_size', 'cmp_mine_type', 'cmp_video_codec', 'cmp_video_codec_profile',
                'cmp_video_codec_level', 'cmp_video_bit_rate', 'cmp_video_frame_rate', 'cmp_video_duration',
                'cmp_width', 'cmp_height']:
            try:
                is_pass = getattr(cmpt, cmp_method)()
            except ErrValueNotFound as e:
                self.log.warning(e)
                continue
            if not is_pass:
                self.log.warning('=> Do {} failed.'.format(cmp_method))
                # Generate error message.
                err_msg = 'Extraction Test Compare Error. {}'.format(cmpt.get_last_cmp_msg())
                raise self.err.TestFailure(err_msg)

        self.uut.adb_log('*** Extraction Test (Sub-test #{}) Is Done'.format(test_info['index']))


    #
    # Test For Check Only Call
    #
    def transcoding_settings(self, media_info):
        """ Generate transcoding settings for each test case. 
        """
        def get_resolution_number(string):
            return int(''.join([ch for ch in string if ch.isdigit()]))

        max_resolution = get_max_api_resolution_options(video_info=media_info)
        self.log.warning('Max Resolutin Can Convert: {}'.format(max_resolution))

        max_res_number = get_resolution_number(max_resolution)
        # Return transcoding combinations
        for video_codec in API_VIDEO_CODECS:
            for container in API_CONTAINERS:
                for resolution in API_TRANSCODING_SETTINGS.iterkeys():
                    if self.test_only_240p:
                        if resolution != '240p': continue
                    if max_res_number < get_resolution_number(resolution):
                        self.log.debug('SKIP Transcoding Case: video_codec={} container={} resolution={}'.format(video_codec, container, resolution))
                        continue
                    yield TranscodingSettingInformation(video_codec, container, resolution, self.duration)

    @add_errmsg_header(errmsg_header='[STATUS-1]')
    def test_check_only_call(self, test_info):
        """ Main Logic of test.
        """
        self.uut.adb_log('*** Start checkOnly call Test (Sub-test #{})...'.format(test_info['index']))

        self.log.debug('rotated_rest_info:\n{}'.format(pformat(test_info['rotated_rest_info'])))
        # Fetch value from ts_info
        ts_info = test_info['ts_info']
        video_codec, container, resolution = ts_info['video']['videoCodec'], ts_info['container'], ts_info['resolution']
        self.log.warning('Support Verify: Convert to video_codec={} container={} resolution={}'.format(video_codec, container, resolution))
        # Check video is not support or not with check_only flag.
        try:
            response = self.uut_owner.get_video_stream(
                file_id=test_info['rotated_rest_info']['id'], container=container, resolution=resolution, video_codec=video_codec,
                duration=self.duration, check_only=True
            )
            self.log.info('* Content:\n{}'.format(pformat(response.json())))
            is_api_support = True
        except requests.HTTPError, e:
            is_api_support = False

        # Check response is correct or not.
        self.log.info('Check transcoding is support or not...')
        is_support = self.is_transcoding_support(platform=self.uut['model'], media_info=test_info['rotated_prepared_info'], ts_info=ts_info)
        self.log.debug('Support Check: API={} vs Expect={}'.format(is_api_support, is_support))
        if is_api_support != is_support:
            raise self.err.TestFailure('The checkOnly call reponse is not expect: Expect {} but {}'.format(is_support, is_api_support))
        self.log.warning("=> The checkOnly call reponse is correct")

        if is_api_support: # Only check when it success because return message may not decode when 500 status.
            self.verify_checkOnly_call_response(response, test_info)
            self.log.warning("=> The checkOnly call content is correct")
        else:
            self.log.warning("=> The checkOnly call return not support, not check content")

        self.uut.adb_log('*** checkOnly call Test (Sub-test #{}) Is Done'.format(test_info['index']))
        return is_support

    def verify_checkOnly_call_response(self, response, test_info):
        self.log.debug('Content: {}'.format(response.text))
        try:
            # {"maxFrameRate":30,"maxResolution":"480p"}
            resp = response.json()
            # Verify maxResolution
            max_resolution = get_max_api_resolution_options(video_info=test_info['rotated_prepared_info'])
            if max_resolution != resp['maxResolution']:
                raise RuntimeError('maxResolution is not correct: Expect {} but {}'.format(max_resolution, resp['maxResolution']))
            # Verify maxFrameRate
            ts_info = test_info['ts_info']
            if ts_info['video']['frameRate'] != resp['maxFrameRate']:
                raise RuntimeError('maxFrameRate is not correct: Expect {} but {}'.format(
                    ts_info['video']['frameRate'], resp['maxFrameRate']))
        except Exception, e:
            self.log.exception(e)
            raise self.err.TestFailure('Verify checkInly call reponse failed: {}'.format(e))

    def is_transcoding_support(self, platform, media_info, ts_info):
        check_rules = []
        if platform == 'monarch':
            check_rules = Monarch_Transcoding_Rules
        elif platform == 'pelican':
            check_rules = Pelican_Transcoding_Rules
        elif platform == 'yodaplus':
            check_rules = YodaPlus_Transcoding_Rules
        else:
            raise self.err.TestFailure('Unknown platform: {}'.format(platform))

        for rule in check_rules:
            for codec_limit in rule['src_codecs']:
                # TODO: Pre-create checkers if it has performace issue.
                checker = SPECLimitationChecker(
                    limit_src=SPECLimitationInformation(
                        codec=codec_limit['codec'], profile=codec_limit['profile'], level=codec_limit['level'],
                        frame_rate=rule['src_max_frame_rate'], width=rule['src_max_width'], height=rule['src_max_height']
                    ),
                    limit_dest=SPECLimitationInformation(
                        codec=rule['dst_codec'], profile=None, level=None, frame_rate=rule['dst_max_frame_rate'],
                        width=rule['dst_max_width'], height=rule['dst_max_height']
                    ),
                    logging=self.log
                )
                if checker.is_support(target_src=media_info, target_dest=ts_info):
                    self.log.debug('=> Transcoding Is Support')
                    return True
                self.log.debug('=> Transcoding Is Not Support')
        return False


    #
    # Test For Media Transcoding
    #
    def handle_existing_FFmpeg_process(self, delay=5, timeout=60*60*24, time_to_kill=15):
        """ If time_to_kill is given, then it will try to kill all of existing FFmpg process,
        or wait for them exit util timeout. 
        """
        self.log.info('Make sure there is no FFmpg process execute in background...')
        if not self.adb.wait_all_FFmpeg_finish(delay, timeout, time_to_kill):
            raise self.err.TestFailure('Timeout waiting for FFmpeg processes finish.')

    def reboot_device_if_zombie_found(self):
        """ Return Ture if device rebooted. """
        rebooted = False
        if self.reboot_if_zombie_found:
            rebooted = self.adb.reboot_if_zombie_found()
        return rebooted

    @add_errmsg_header(errmsg_header='[STATUS-2]')
    def test_media_transcoding(self, test_info):
        """ Main Logic of test.
        """
        self.uut.adb_log('*** Start Media Transcoding Test (Sub-test #{})...'.format(test_info['index']))
        self.handle_existing_FFmpeg_process()
        rebooted = self.reboot_device_if_zombie_found()
        self.log.warning('Convert to video_codec={} container={} resolution={}'.format(
            test_info['ts_info']['video']['videoCodec'], test_info['ts_info']['container'], test_info['ts_info']['resolution']
        ))
            
        def get_transcode_data():
            response = self.uut_owner.get_video_stream(
                file_id=test_info['rotated_rest_info']['id'], video_codec=test_info['ts_info']['video']['videoCodec'],
                container=test_info['ts_info']['container'], resolution=test_info['ts_info']['resolution'],
                duration=self.duration, timeout=self.transcoding_request_timeout
            )
            save_to_file(iter_obj=response.iter_content(chunk_size=1024), file_name=self.local_file)
            return response

        try:
            # Do video transcoding (retry 10 times for reboot process).
            if rebooted: self.log.info('The next RestSDK call could retry 10 times cause it invoked after device rebooted...')
            response = retry(
                func=get_transcode_data,
                excepts=(requests.HTTPError, TypeError, AttributeError), delay=10, max_retry=10 if rebooted else 0, log=self.log.warning
            )
            self.log.info('Elapsed Time: {} sec.'.format(response.elapsed.total_seconds()))
            self.verify_transcoding_header(response, test_info)
            self.verify_transcoding_content(test_info)
        except Exception as e:
            if os.path.exists(self.local_file): # For tracing bug.
                save_path = os.path.join(self.env.output_folder, uuid4().hex+'.mkv')
                self.log.warning('Move stream file to {} for tracing'.format(save_path))
                os.rename(self.local_file, save_path)
            raise
        finally:
            self.adb.is_any_FFmpeg_running() # just to check status again.
            if os.path.exists(self.local_file):
                os.remove(self.local_file)

            self.uut.adb_log('*** Media Transcoding Test (Sub-test #{}) Is Done'.format(test_info['index']))

    def verify_transcoding_header(self, response, test_info):
        self.log.info("Response Header: \n{}".format(pformat(response.headers)))
        container = test_info['ts_info']['container']
        if API_MIMETYPE.get(container, '').lower() != response.headers.get('Content-Type', '').lower():
            self.log.info('Verify header: FAILED.')
            self.uut_owner.log_response(response, logger=self.log.warning)
            with open(self.local_file) as f:
                self.log.warning('Response content(one line): {}'.format(f.readline()))
            raise self.err.TestFailure('Response header is incorrect.')
        self.log.info('Verify header: PASSED.')

    def verify_transcoding_content(self, test_info):
        transcoded_stream = VideoConverter(path=self.local_file, logging=self.log).convert()
        test_info['converted_info'] = transcoded_stream

        # Convert all inforamtion to the same data format.
        self.log.debug('transcoded_stream:\n{}'.format(pformat(transcoded_stream)))
        self.log.debug('ts_info:\n{}'.format(pformat(test_info['ts_info'])))

        aspect_ratio = test_info['rotated_prepared_info']['video']['width'] / float(test_info['rotated_prepared_info']['video']['height'])
        # Compare values.
        src_dict = copy.deepcopy(test_info['ts_info'])
        if not src_dict['video']['duration']: # Set duration value if duration of transcoding is not change.
            src_dict['video']['duration'] = test_info['rest_resp']['video']['duration']
        # Rotate video since it will auto-rotate by FFmpeg.
        if self._do_need_rotate_by_metadata(info=test_info['rotated_prepared_info']):
            self._rotate_video_by_metadata(info=src_dict, angle=test_info['rotated_prepared_info']['rotate'])
        cmpt = Comparator(src_set=src_dict, cmp_set=transcoded_stream, logging=self.log)
        for cmp_method in ['verify_stream_container', 'cmp_video_codec',
                #'verify_stream_video_bit_rate', 'cmp_video_duration', 'verify_stream_frame_rate', # Disable since KAM200-1057.
                'verify_stream_resolution']:
            try:
                # Get args for compare method.
                args = {
                    'verify_stream_frame_rate': [test_info['rotated_prepared_info']['video']['frameRate']],
                    'verify_stream_resolution': [aspect_ratio],
                    'cmp_video_duration': [0.05] # Some cases is changed then > 3%.
                }.get(cmp_method, ())
                # Do comparing.
                is_pass = getattr(cmpt, cmp_method)(*args)
            except ErrValueNotFound as e:
                self.log.warning(e)
                continue
            if not is_pass:
                self.log.warning('=> Do {} failed.'.format(cmp_method))
                err_msg = 'Verify Converted Stream Error. {}'.format(cmpt.get_last_cmp_msg())
                raise self.err.TestFailure(err_msg)


if __name__ == '__main__':
    parser = IntegrationTestArgument("""\
        *** RESTSDKTranscoding on Kamino Android ***
        Examples: ./run.sh transcoding_tests/integration_tests/restsdk_transcoding.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-db_path', '--db_file_path', help='Path of db file', metavar='PATH')
    parser.add_argument('-db_url', '--db_file_url', help='URL of db file to download from file server', metavar='URL')
    parser.add_argument('-duration', '--duration', help='Duration value to convent all test video', type=int, metavar='DURATION', default=5000)
    parser.add_argument('-nid', '--not_init_data', help='Use existing data for test', action='store_true', default=False)
    parser.add_argument('-nell', '--not_export_logcat_log', help="Don't export logcat logs at end of each sub-test", action='store_true', default=False)
    parser.add_argument('-nuel', '--not_upload_end_log', help="Don't upload logs to sumologic at end of each sub-test", action='store_true', default=False)
    parser.add_argument('-csf', '--case_start_from', help="Sub-case number start from", type=int, metavar='NUMBER', default=0)
    parser.add_argument('-to240p', '--test_only_240p', help="Do test with 240p cases", action='store_true', default=False)
    parser.add_argument('-ldp', '--local_data_path', help="Upload test video from local path via RestSDK call")
    parser.add_argument('-rizf', '--reboot_if_zombie_found', help="Reboot device when zombie process found", action='store_false', default=True)

    test = RESTSDKTranscoding(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
