# -*- coding: utf-8 -*-

__author__ = "Estvan <Estvan.Huang@wdc.com>"

# std modules
import sys
import os
import shutil
import random
import time
import threading
from uuid import uuid4
# 3rd party
import requests
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.adblib import ADB
from platform_libraries.compare import compare_images
from platform_libraries.constants import Kamino
from platform_libraries.pyutils import retry, save_to_file
from platform_libraries.restAPI import RestAPI
from platform_libraries.sql_client import ThumbnailsDatabase
# test case
from functional_tests.wifi.ap_connect import APConnect


atomic_lock = threading.RLock()

def atomic(func):
    def _atomic(*args, **kwargs):
        try:
            atomic_lock.acquire()
            return func(*args, **kwargs)
        finally:
            atomic_lock.release()
    return _atomic


class APRebootIOTest(APConnect):

    TEST_SUITE = 'IO_Stress_Tests'
    TEST_NAME = 'AP_Reboot_IO_Stress_Test'

    SETTINGS = {
        'uut_owner': True,
        'disable_loop': True
    }

    def declare(self):
        self.global_timeout = 15
        # Local data path.
        self.LOCAL_UPLOAD_FOLDER = os.path.join(os.getcwd(), 'stressio_upload')
        self.LOCAL_DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'stressio_download')
        self.LOCAL_THUMB_FOLDER = os.path.join(os.getcwd(), 'stressio_thumbs')
        self.LOCAL_THUMB_DB_PATH = os.path.join(os.getcwd(), 'stressio_thumbs/thumbs.db')
        # File server path.
        self.THUMB_SERVER_PATH = '/test/thumbnails/wifi_io_stress/256M/'
        self.FILE_SERVER_PATH = '/test/wifi_io_stress/256M/'
        # Test Step controls.
        self.ap_power_port = None
        # Flag to record ap status.
        self._poweroff_ap = False
        self._disable_wifi = False
        # Trigger with file names
        self.trigger_on_files = []
        self.break_thread = None

    def init(self):
        # Upload location. 
        self.NAS_UPLOAD_FOLDER = 'data_uploaded'  # Use for upload case, files uploads from local to here
        self.NAS_DOWNLOAD_FOLDER = 'data_for_download'  # Use for download case, file will be download from here to local client
        self.NAS_DOWNLOAD_FOLDER_ID = ''
        # Data/User list.
        self.FILE_LIST = [] # File name list of test set.
        self.FILE_DOWNLOAD_ID_LIST = [] # File ID list of test set in RestSDK.
        self.FILE_MD5_LIST = [] # md5sum list of test set.
        self.USER_CLIENT_LIST = [self.uut_owner]  # We will have at least 1 user client (device owner).
        self.USER_ADB_LIST = [self.adb]  # We will have at least 1 user client (device owner).
        self.USER_ID_LIST = [str(self.uut_owner.get_user_id())]
        # Test result.
        self.TOTAL_PASSED = 0
        self.TOTAL_FAILED = 0

    def before_test(self):
        self._poweroff_ap = False
        self._disable_wifi = False
        self.log.info("#"*75)
        self.log.info("### Step 1: Create users and attach them in UUT device ###")
        self.init_test_users(user_number=self.user_number)
        self.log.info("#"*75)
        self.log.info("### Step 2: Prepare local test folders ###")
        self.create_upload_folder()
        self.download_thumbnails_dataset()
        self.download_test_dataset()
        self.create_download_folder()
        self.create_user_download_folders()
        self.log.info("Local test folders are ready")
        self.log.info("#"*75)
        self.log.info("### Step 3: Prepare UUT test folders ###")
        self.prepare_UUT_test_folders()
        self.init_local_md5_list()
        self.log.info("### Prepare environment finished ###")
        self.log.info("#"*75)
        # Reocrd logcat during test.
        self.serial_client.start_background_logcat()

    def init_test_users(self, user_number):
        """ Create users and attach them in UUT device. """
        self.uut_owner._retry_times = 0 # Not retry anything.
        if not self.user_number > 1:
            return

        for user_idx in xrange(1, user_number):
            user_name = 'wdctest_stressio_{}+qawdc@test.com'.format(user_idx)
            rest_client = RestAPI(
                self.env.uut_ip, self.env.cloud_env, user_name, 'Test1234', log_name='restAPI.User{}'.format(user_idx),
                stream_log_level=self.env.stream_log_level
            )
            rest_client._retry_times = 0 # Not retry anything.
            self.USER_CLIENT_LIST.append(rest_client)
            adb_client = ADB(
                uut_ip=self.env.uut_ip, port=self.env.uut_port, adbServer=self.env.adb_server_ip, adbServerPort=self.env.adb_server_port,
                log_name='adblib.User{}'.format(user_idx), stream_log_level=self.env.stream_log_level
            )
            self.USER_ADB_LIST.append(adb_client)
            self.USER_ID_LIST.append(rest_client.get_user_id())

    def create_upload_folder(self):
        self.log.info("Create upload folder")
        if os.path.exists(self.LOCAL_UPLOAD_FOLDER):
            shutil.rmtree(self.LOCAL_UPLOAD_FOLDER)
        os.mkdir(self.LOCAL_UPLOAD_FOLDER)

    def download_thumbnails_dataset(self):
        self.log.info("Download thumbnails files from file server")
        download_path = '{0}{1}'.format('http://{}'.format(self.file_server), self.THUMB_SERVER_PATH)
        cur_dir = self.THUMB_SERVER_PATH.count('/')
        url = 'wget -np --no-host-directories --cut-dirs={0} -r {1} -P {2}'.format(cur_dir, download_path, self.LOCAL_THUMB_FOLDER)
        if self.private_network:
            url += ' --no-passive'
        os.popen(url)

    def download_test_dataset(self):
        self.log.info("Download test files from file server to upload folder")
        download_path = '{0}{1}'.format('http://{}'.format(self.file_server), self.FILE_SERVER_PATH)
        cur_dir = self.FILE_SERVER_PATH.count('/')
        url = 'wget -np --no-host-directories --cut-dirs={0} -r {1} -P {2}'.format(cur_dir, download_path, self.LOCAL_UPLOAD_FOLDER)
        if self.private_network:
            url += ' --no-passive'
        os.popen(url)

        # load file name to file list.
        for (dirpath, dirnames, filenames) in os.walk(self.LOCAL_UPLOAD_FOLDER):
            self.FILE_LIST.extend(filenames)
            break # one level.

    def create_download_folder(self):
        self.log.info("Create download folder")
        if os.path.exists(self.LOCAL_DOWNLOAD_FOLDER):
            shutil.rmtree(self.LOCAL_DOWNLOAD_FOLDER)
        os.mkdir(self.LOCAL_DOWNLOAD_FOLDER)

    def create_user_download_folders(self):
        self.log.info("Create download sub folder for each user")
        for user_id in range(int(self.user_number)):
            local_folder_name = os.path.join(self.LOCAL_DOWNLOAD_FOLDER, 'user_{}'.format(user_id))
            os.mkdir(local_folder_name)

    def prepare_UUT_test_folders(self):
        self.log.info("Upload test files into owner's folder for download test case")
        # Create basis folder.
        self.uut_owner.commit_folder(folder_name=self.NAS_DOWNLOAD_FOLDER)
        self.NAS_DOWNLOAD_FOLDER_ID = self.USER_CLIENT_LIST[0].get_data_id_list(type='folder', data_name=self.NAS_DOWNLOAD_FOLDER)
        self.log.warning('nas_folder_id:{}'.format(self.NAS_DOWNLOAD_FOLDER_ID))

        # Upload test dataset for download test.
        for index, file in enumerate(self.FILE_LIST):
            with open(os.path.join(self.LOCAL_UPLOAD_FOLDER, file), 'rb') as f:
                self.log.info("Uploading file: {0} into test folder {1}".format(file, self.NAS_DOWNLOAD_FOLDER))
                self.uut_owner.chuck_upload_file(file_object=f, file_name=file, parent_folder=self.NAS_DOWNLOAD_FOLDER)
            file_id = self.uut_owner.get_data_id_list(type='file', parent_id=self.NAS_DOWNLOAD_FOLDER_ID, data_name=file)
            # Add share access permission to all test users.
            for user_id in self.USER_ID_LIST:
                self.USER_CLIENT_LIST[0].set_permission(file_id, user_id=user_id, permission="ReadFile")
            self.FILE_DOWNLOAD_ID_LIST.append(file_id)

    def init_local_md5_list(self):
        self.log.info("Update the MD5 checksum list for comparison standard")
        for file in self.FILE_LIST:
            md5_before = self.local_md5_checksum(os.path.join(self.LOCAL_UPLOAD_FOLDER, file))
            self.FILE_MD5_LIST.append(md5_before)

        if len(self.FILE_MD5_LIST) != len(self.FILE_LIST):
            raise RuntimeError('Some of the MD5 checksum is missing, stop the test')

    @atomic
    def trace_issue(self):
        # Debug for KAM200-6847.
        try:
            self.serial_client.logger.info('Tracing device status...')
            self.serial_client.serial_write('ifconfig wlan0')
            time.sleep(0.5)
            self.serial_client.serial_write('cat /proc/net/arp')
            time.sleep(0.5)
            self.serial_client.serial_write('route')
            time.sleep(0.5)
            self.serial_client.serial_write('iptables -L –n')
            time.sleep(0.5)
            self.serial_client.serial_write('ping -c 10 8.8.8.8')
            time.sleep(10)
            self.serial_client.serial_read_all()
        except Exception, e:
            self.serial_client.logger.exception(e)

    def test(self):

        def break_call(user_num):
            if user_num == 0: # Depend on device owner.
                if self.power_switch: # Reactivate wifi by power off and of AP.
                    return self.delay_reboot_ap(delay=5)
                return self.delay_reactivate_wifi(delay=5) # Reactivate wifi by commands.
            return None

        def _run_test(test_results, iteration, user_num, test_type):
            rest_client = self.USER_CLIENT_LIST[user_num]
            adb_client = self.USER_ADB_LIST[user_num]
            total_test_passed = 0
            total_test_failed = 0
            for idx in xrange(1, iteration+1):
                if test_type == 'm':
                    run_type = random.choice(['u', 'd'])  # Mixed type, random choose r or w
                else:
                    run_type = test_type

                rest_client.log.info(
                    '### User{0}: iteration {1}, Type: {2} Start ###'.format(user_num, idx, 'Download' if run_type == 'd' else 'Upload')
                )
                iter_start_time = time.time()

                try:
                    if run_type == 'd':
                        test_result = self.resumable_download_test(user_num, break_call)
                    else:
                        test_result = self.resumable_upload_test(user_num, break_call)

                    iter_elapsed_time = time.time() - iter_start_time
                    if test_result:
                        total_test_passed += 1
                        rest_client.log.info('### User{0}: iteration {1} is Passed, Elapsed Time: {2}'.format(user_num, idx, iter_elapsed_time))
                    else:
                        total_test_failed += 1
                        rest_client.log.error('### User{0}: iteration {1} is Failed'.format(user_num, idx))
                        self.save_logcat(adb_client, path='{0}/user{1}#{2}-{3}.logcat'.format(self.env.output_folder, user_num, idx, run_type))
                except Exception, e:
                    rest_client.log.exception(e)
                    total_test_failed += 1
                    rest_client.log.error('### User{0}: iteration {1} is Failed'.format(user_num, idx))
                    self.save_logcat(adb_client, path='{0}user{1}#{2}-{3}.logcat'.format(self.env.output_folder, user_num, idx, run_type))

            test_results.append([total_test_passed, total_test_failed])

        # Setting global timeout for uploading tests, not set in upload method.
        self.uut_owner.set_global_timeout(timeout=self.global_timeout)

        self.trigger_on_files = ['720P_H.264.mp4']

        thread_list = []
        test_results = []
        for user_num in range(len(self.USER_CLIENT_LIST)):
            thread = threading.Thread(
                target=_run_test,
                kwargs={'test_results': test_results, 'iteration': self.iteration_per_user, 'user_num': user_num, 'test_type': self.test_type}
            )
            thread.start()
            thread_list.append(thread)
            self.log.info("User{0}: {1}".format(user_num, thread))

        for thread in thread_list:
            self.log.info("Join {}...".format(thread))
            thread.join()
            self.log.info("Done: {}".format(thread))
            test_result = test_results.pop()
            self.TOTAL_PASSED += int(test_result[0])
            self.TOTAL_FAILED += int(test_result[1])

        # Recover setting we changed.
        self.uut_owner.reset_global_timeout()

        self.log.info("Total Passed: {}".format(self.TOTAL_PASSED))
        self.log.info("Total Failed: {}".format(self.TOTAL_FAILED))
        self.data.test_result['StressIOTestPassed'] = self.TOTAL_PASSED
        self.data.test_result['StressIOTestFailed'] = self.TOTAL_FAILED


    def resumable_upload_test(self, user_num, break_call=None):
        rest_client = self.USER_CLIENT_LIST[user_num]
        adb_client = self.USER_ADB_LIST[user_num]
        user_id = self.USER_ID_LIST[user_num].replace('auth0|', 'auth0\|')
        uploaded_file_dict = {}
        rest_client.log.info("Create a folder: {} for User{} to upload files".format(self.NAS_UPLOAD_FOLDER, user_num))
        self.retry( # Retry for it broken by first user.
            func=rest_client.commit_folder, func_kwargs={'folder_name': self.NAS_UPLOAD_FOLDER},
            rest_client=rest_client, adb_client=adb_client
        )
        folder_id = self.retry( # Retry for it broken by first user.
            func=rest_client.get_data_id_list, func_kwargs={'type': 'folder', 'data_name': self.NAS_UPLOAD_FOLDER},
            rest_client=rest_client, adb_client=adb_client
        )
        rest_client.log.warning("Folder id: {}".format(folder_id))
        try:
            for index, file in enumerate(self.FILE_LIST):
                # Upload file.
                with open(os.path.join(self.LOCAL_UPLOAD_FOLDER, file), 'rb') as f:
                    try:
                        # Make sure feature works.
                        self.wait_for_restsdk_works(rest_client, timeout=60*10, adb_client=adb_client)
                        # Make sure there is no resumable acceess before breaking.
                        APRebootIOTest.AccessProtect(user_num, log_inst=rest_client.log).wait_all_access()
                        # Trigger breaking if file name is matched.
                        self.trigger_by_filename(file, break_call, user_num)
                        # Start to upload.
                        rest_client.log.info("### User{0}: Start to upload file: {1} ###".format(user_num, file))
                        upload_start_time = time.time()
                        rest_client.chuck_upload_file(file_object=f, file_name=file, parent_id=folder_id, timeout=5, set_global_timeout=False)
                        # Wait for break thread if need.
                        self.wait_for_break_thread(log_inst=rest_client.log)
                    except (rest_client.ChuckUploadFailed), e: # Resumable upload once.
                        rest_client.log.warning("### User{0}: Upload file break, error message: {1}. Resuming... ###".format(user_num, repr(e)), exc_info=True)
                        # Make sure feature works.
                        self.wait_for_break_thread(log_inst=rest_client.log)
                        # Record this access to let the first user know it doing resumable access.
                        with APRebootIOTest.AccessProtect(user_num, log_inst=rest_client.log):
                            self.wait_for_restsdk_works(rest_client, timeout=60*10, adb_client=adb_client, wait_more_seconds=True)
                            # Continue to upload.
                            try:
                                if not e.parent_id: rest_client.log.warning('[TRACE] Has no parent_id!!')
                                rest_client.chuck_upload_file(file_object=f, file_name=e.file_name, file_id=e.file_id, parent_id=folder_id, \
                                    start_offset=e.start_offset, timeout=15, set_global_timeout=False)
                            except rest_client.ChuckUploadFailed, e: # Handle the DONE request's response was missed by network disconnect.
                                if not e.src_exception or not isinstance(e.src_exception, requests.HTTPError) or e.src_exception.response is None or \
                                    e.src_exception.response.status_code != 404 or 'done=true' not in e.src_exception.response.url:
                                    raise
                                rest_client.log.warning("Resumable upload file: {} is failed, but it looks upload completed at previous step, check it...".format(file))
                                rest_client.get_data_by_id(data_id=e.file_id)
                                rest_client.log.warning('File {}: Upload completed'.format(file))

                    upload_elapsed_time = time.time() - upload_start_time
                    rest_client.log.info("### User{0}: Upload file: {1} complete. Time elapsed: {2} ###".format(user_num, file, upload_elapsed_time))

                # Get file ID.
                file_id = self.retry( # Retry for it broken by first user.
                    func=rest_client.get_data_id_list, func_kwargs={'type': 'file', 'data_name': file, 'parent_id': folder_id},
                    rest_client=rest_client, adb_client=adb_client
                )
                rest_client.log.debug('File ID: {}'.format(file_id))
                uploaded_file_dict[file] = file_id

                # Uploaded file comparison.
                checksum = self.retry( # Retry for it broken by first user.
                    func=self.uut_md5_checksum, func_kwargs={'adb_client': adb_client, 'remote_path': os.path.join(Kamino.USER_ROOT_PATH, user_id, self.NAS_UPLOAD_FOLDER, file)},
                    rest_client=rest_client, adb_client=adb_client, log=adb_client.log.info, retry_lambda=lambda x: not x, max_retry=30
                )
                if not self.compare_md5_checksum(user_num, file, self.FILE_MD5_LIST[index], checksum):
                    self.trace_issue()
                    return False

                # Thumbnail comparison.
                result = self.retry( # Retry for it broken by first user.
                    func=self.thumbnail_comparison, func_kwargs={'user_num': user_num, 'file_id': file_id, 'file': file},
                    rest_client=rest_client, adb_client=adb_client, retry_lambda=lambda x: not x
                )
                if not result:
                    self.trace_issue()
                    return False
            return True
        except Exception as e:
            rest_client.log.error("### [TestFailed] User{0}: Failed to upload file, error message: {1} ###".format(user_num, repr(e)), exc_info=True)
            # For double check file status when got an error.
            adb_client.executeShellCommand('ls {}/'.format(os.path.join(Kamino.USER_ROOT_PATH, user_id, self.NAS_UPLOAD_FOLDER)), timeout=3*60, consoleOutput=True)
            self.trace_issue()
            return False
        finally:
            # Delete uploaded files by folder ID.
            try:
                result, delete_elapsed_time = self.retry( # Retry for it broken by first user.
                    func=rest_client.delete_file, func_kwargs={'data_id': folder_id},
                    retry_function='Without_404', rest_client=rest_client, adb_client=adb_client, delay=5
                )
                rest_client.log.info("### User{0}: Delete folder: {1} complete. Elapsed time: {2}".format(user_num, folder_id, delete_elapsed_time))
            except: # Keep to delete files.
                pass # Logging error in restAPI library. 

    def resumable_download_test(self, user_num, break_call=None):
        rest_client = self.USER_CLIENT_LIST[user_num]
        adb_client = self.USER_ADB_LIST[user_num]
        try:
            for index, file in enumerate(self.FILE_LIST):
                try:
                    # Make sure feature works.
                    self.wait_for_restsdk_works(rest_client, timeout=60*10, adb_client=adb_client)
                    # Make sure there is no resumable acceess before breaking.
                    APRebootIOTest.AccessProtect(user_num, log_inst=rest_client.log).wait_all_access()
                    # Trigger breaking if file name is matched.
                    self.trigger_by_filename(file, break_call, user_num)
                    # Start to download.
                    rest_client.log.info("### User{0}: Start to download file: {1} ###".format(user_num, file))
                    download_start_time = time.time()
                    content = rest_client.get_file_content_v3(self.FILE_DOWNLOAD_ID_LIST[index]).content
                    with open(os.path.join(self.LOCAL_DOWNLOAD_FOLDER, 'user_{}'.format(user_num), file), 'wb') as f:
                        f.write(content)
                    # Wait for break thread if need.
                    self.wait_for_break_thread(log_inst=rest_client.log)
                except Exception, e: # Resumable download once.
                    rest_client.log.warning("### User{0}: Download file break, error message: {1}. Resuming... ###".format(user_num, repr(e)), exc_info=True)
                    # Make sure feature works.
                    self.wait_for_break_thread(log_inst=rest_client.log)
                    # Record this access to let the first user know it doing resumable access.
                    with APRebootIOTest.AccessProtect(user_num, log_inst=rest_client.log):
                        self.wait_for_restsdk_works(rest_client, timeout=60*10, adb_client=adb_client, wait_more_seconds=True)
                        # Continue to download.
                        content = rest_client.get_file_content_v3(self.FILE_DOWNLOAD_ID_LIST[index]).content
                        with open(os.path.join(self.LOCAL_DOWNLOAD_FOLDER, 'user_{}'.format(user_num), file), 'wb') as f:
                            f.write(content)

                download_elapsed_time = time.time() - download_start_time
                rest_client.log.info("### User{0}: Download file: {1} complete. Time elapsed: {2} ###".format(user_num, file, download_elapsed_time))

                # Downloaded file comparison.
                checksum = self.local_md5_checksum(os.path.join(self.LOCAL_DOWNLOAD_FOLDER, 'user_{}'.format(user_num), file))
                if not self.compare_md5_checksum(user_num, file, self.FILE_MD5_LIST[index], checksum):
                    self.trace_issue()
                    return False
            return True
        except Exception as e:
            rest_client.log.error("### [TestFailed] User{0}: Failed to download file, error message: {1} ###".format(user_num, repr(e)))
            self.trace_issue()
            return False
        finally:
            for file in self.FILE_LIST:
                try:
                    file_path = os.path.join(self.LOCAL_DOWNLOAD_FOLDER, 'user_{}'.format(user_num), file)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception, e: # Keep to delete files.
                    self.log.warning(e, exc_info=True)

    @atomic
    def trigger_by_filename(self, filename, break_call, *arg, **kwargs):
        if break_call and filename in self.trigger_on_files:
            bt = break_call(*arg, **kwargs)
            if bt:
                self.break_thread = bt
                return self.break_thread
        return None

    @atomic
    def wait_for_break_thread(self, log_inst):
        if not self.break_thread:
            return
        log_inst.warning('Wait for break behvior finish...')
        self.break_thread.join()
        self.break_thread = None
        log_inst.warning('Break behvior is finish')

    def wait_for_restsdk_works(self, rest_client, timeout, adb_client=None, wait_more_seconds=False):
        if not rest_client.wait_for_restsdk_works(timeout, wait_more_seconds):
            self.trace_issue()
            if adb_client:
                adb_client.log.warning('Check test status by ADB...')
                if adb_client.is_device_pingable():
                    adb_client.log.warning('Device is pingable')
                    adb_client.executeShellCommand(cmd='ps | grep restsdk', consoleOutput=True)
                    adb_client.executeShellCommand(cmd='curl -v 127.0.0.1/sdk/v1/device', consoleOutput=True)
                else:
                    adb_client.log.warning("Device isn't pingable")
            raise RuntimeError('Timeout waiting for REST SDK works: {}s'.format(timeout))

    def local_md5_checksum(self, path):
        response = os.popen('md5sum {}'.format(path))
        if response:
            result = response.read().strip().split()[0]
            return result
        else:
            self.log.error("There's no response from local MD5 checksum")
            return None

    def uut_md5_checksum(self, remote_path, adb_client=None):
        if not adb_client:
            adb_client = self.adb
        response = adb_client.executeShellCommand('busybox md5sum {}'.format(remote_path), timeout=3*60, consoleOutput=True)
        if response[0] and 'No such file or directory' not in response[0]:
            return response[0].strip().split()[0]
        adb_client.log.warning("There's no response from uut md5 checksum")
        # Check folder status.
        adb_client.executeShellCommand('ls {}/..'.format(remote_path), timeout=3*60, consoleOutput=True)
        return None

    def compare_md5_checksum(self, user_num, file, before, after):
        if before == after:
            self.USER_CLIENT_LIST[user_num].log.warning('### User{0}: {1} MD5 comparison is passed ###'.format(user_num, file))
            return True
        self.USER_CLIENT_LIST[user_num].log.error('### [TestFailed] User{0}: {1} MD5 comparison failed! MD5 before: {2}, MD5 after: {3} ###'.format(user_num, file, before, after))
        return False

    def thumbnail_comparison(self, user_num, file_id, file):
        rest_client = self.USER_CLIENT_LIST[user_num]
        rest_client.log.debug('Start to do thumbnail comparison')
        try:
            local_thumb_path = self.get_local_thumb_path(file)
            if not local_thumb_path: # Thumbnail not support.
                return True
            # Download thumbnail.
            start_time = time.time()
            restsdk_thumb_path = self.get_restsdk_thumb_path(user_num, file_id)
            download_elapsed_time = time.time() - start_time
            if not restsdk_thumb_path:
                rest_client.log.error('### User{0}: {1} thumbnail download failed! ###'.format(user_num, file))
                return False
            rest_client.log.info("### User{0}: Get file thumbnail: {1} complete. Time elapsed: {2} ###".format(user_num, file, download_elapsed_time))
            # Compare image.
            keep_thumb = False
            result = compare_images(local_thumb_path, restsdk_thumb_path, threshold=0.05, log_inst=rest_client.log)
            if not result:
                rest_client.log.error('### User{0}: {1} thumbnail comparison failed! ###'.format(user_num, file))
                keep_thumb = True
                return False
            rest_client.log.warning('### User{0}: {1} thumbnail comparison is passed! ###'.format(user_num, file))
            return True
        finally:
            if 'restsdk_thumb_path' in locals() and isinstance(restsdk_thumb_path, basestring) and os.path.exists(restsdk_thumb_path):
                if keep_thumb: # For tracing issue.
                    save_path = os.path.join(self.env.output_folder, uuid4().hex+'.jpg')
                    rest_client.log.warning('### User{0}: {1} thumbnail move to {2} for tracing ###'.format(user_num, file, save_path))
                    os.rename(restsdk_thumb_path, save_path)
                else: # Delete downloaded thumb.
                    os.remove(restsdk_thumb_path)

    def get_local_thumb_path(self, file):
        with ThumbnailsDatabase(db_file=self.LOCAL_THUMB_DB_PATH) as db_client:
            sub_path = db_client.get_file_by_name(filename=file, size='200c')
            if not sub_path:
                return None
            return os.path.join(self.LOCAL_THUMB_FOLDER, sub_path)

    def get_restsdk_thumb_path(self, user_num, file_id):
        try:
            tmp_path = os.path.join(self.LOCAL_DOWNLOAD_FOLDER, '_thumb{}.jpg'.format(user_num))
            response = self.USER_CLIENT_LIST[user_num].get_file_content_v3(file_id, size='200c', temp_size_max=50)
            save_to_file(iter_obj=response.iter_content(chunk_size=1024), file_name=tmp_path)
            return tmp_path
        except Exception as e:
            self.log.exception(str(e))
            return None

    def after_test(self):
        self.log.info('Clean up the test environment...')
        self.log.info('Removing local folders')
        shutil.rmtree(self.LOCAL_UPLOAD_FOLDER)
        shutil.rmtree(self.LOCAL_DOWNLOAD_FOLDER)
        shutil.rmtree(self.LOCAL_THUMB_FOLDER)

        if self.NAS_DOWNLOAD_FOLDER_ID:
            self.log.info('Removing uut test folder')
            self.uut_owner.delete_file(self.NAS_DOWNLOAD_FOLDER_ID)

        if self._disable_wifi:
            self.ap.enable_5G_wifi()
            self._disable_wifi = False

        if self._poweroff_ap:
            self.power_switch.power_on(self.ap_power_port)
            self._poweroff_ap = False
        # Recovery setting
        self.uut_owner._retry_times = 3

    def delay_reboot_ap(self, delay):
        if self._poweroff_ap:
            self.log.warning('Trigger reboot AP, but it is already rebooted.')
            return
        self.log.info('Reboot AP after {}s...'.format(delay))
        t = threading.Thread(target=self.reboot_ap, kwargs={'delay': delay})
        t.start()
        return t

    def reboot_ap(self, delay=None):
        log_inst = self.USER_CLIENT_LIST[0]
        if delay:
            time.sleep(delay)
        try:
            self.log.info('Reboot AP...')
            retry(func=self.poweroff_ap, delay=5, max_retry=12, log=log_inst.log.info)
            retry(func=self.poweron_ap, delay=5, max_retry=12, log=log_inst.log.info)
            self.update_device_ip(restart_adbd=False) # Multithread issue?
            self.log.info('Reboot AP is done.')
        except Exception, e:
            log_inst.log.exception('Got an error when reboot AP: {}'.format(e))

    def delay_reactivate_wifi(self, delay):
        if self._disable_wifi:
            self.log.warning('Disabling Wi-Fi, but it is already disabled.')
            return
        self.log.info('Reactivate Wi-Fi after {}s...'.format(delay))
        t = threading.Thread(target=self.reactivate_wifi, kwargs={'delay': delay})
        t.start()
        return t

    def reactivate_wifi(self, delay=None):
        log_inst = self.USER_CLIENT_LIST[0]
        if delay:
            time.sleep(delay)
        try:
            self.log.info('Reactivate 5G Wi-Fi...')
            self._disable_wifi = True
            self.ap.disable_5G_wifi() # TODO: Retry it if need.
            self._disable_wifi = False
            self.ap.enable_5G_wifi()
            self.update_device_ip(restart_adbd=False) # Multithread issue?
            self.log.info('Reactivate 5G Wi-Fi is done.')
        except Exception, e:
            log_inst.log.exception('Got an error when reactivate Wi-Fi: {}'.format(e))

    def retry(self, rest_client, func, func_kwargs={}, adb_client=None, timeout=60*10, retry_function=None, **kwargs):
        def retry_func():
            self.wait_for_restsdk_works(rest_client, timeout=timeout, adb_client=adb_client)
            return func(**func_kwargs)

        def retry_func_without_404():
            self.wait_for_restsdk_works(rest_client, timeout=timeout, adb_client=adb_client)
            try:
                return func(**func_kwargs)
            except requests.HTTPError, e:
                if e.response is not None and e.response.status_code == 404:
                    return
                raise

        return retry(
            func={ # TODO# refime me to better.
                'Without_404': retry_func_without_404
            }.get(retry_function, retry_func),
            excepts=kwargs.pop('excepts') if 'excepts' in kwargs else (Exception),
            delay=kwargs.pop('delay') if 'delay' in kwargs else 15,
            max_retry=kwargs.pop('max_retry') if 'max_retry' in kwargs else 5,
            log=kwargs.pop('log') if 'log' in kwargs else rest_client.log.info,
            **kwargs
        )

    def save_logcat(self, adb_client, path):
        try:
            adb_client.logcat_to_file(file_name=path)
        except Exception, e:
            adb_client.log.warning(e, exc_info=True)

    class AccessProtect(object):
        """ Make sure all access not be break by the first user.
        """
 
        access_users = []

        def __init__(self, user_num, log_inst=None, break_user_num=0):
            self.user_num = user_num
            self.log_inst = log_inst
            self.break_user_num = break_user_num

        def __enter__(self):
            if self.break_user_num == self.user_num:
                if self.log_inst: self.log_inst.debug('User {} is break user [enter]'.format(self.user_num))
                return
            if self.user_num in self.access_users:
                #if self.log_inst: self.log_inst.warning('User {} not finish previous access yet.'.format(self.user_num))
                if self.log_inst: self.log_inst.critical('User {} not finish previous access yet.'.format(self.user_num))
                return
            self.access_users.append(self.user_num)
            #if self.log_inst: self.log_inst.debug('User {} doing access.'.format(self.user_num))
            if self.log_inst: self.log_inst.critical('User {} doing access.'.format(self.user_num))
     
        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.break_user_num == self.user_num:
                if self.log_inst: self.log_inst.debug('User {} is break user [exit]'.format(self.user_num))
                return
            if self.user_num not in self.access_users:
                #if self.log_inst: self.log_inst.warning('User {} is alreay doing access.'.format(self.user_num))
                if self.log_inst: self.log_inst.critical('User {} is not in access list.'.format(self.user_num))
                return
            self.access_users.pop(self.access_users.index(self.user_num))
            #if self.log_inst: self.log_inst.debug('User {} finish access.'.format(self.user_num))
            if self.log_inst: self.log_inst.critical('User {} finish access.'.format(self.user_num))

        def wait_all_access(self):
            if self.break_user_num != self.user_num:
                if self.log_inst: self.log_inst.debug('User {} exit [wait_all_access]'.format(self.user_num))
                return
            while self.access_users:
                #if self.log_inst: self.log_inst.debug('Users still access: {}'.format(self.access_users))
                if self.log_inst: self.log_inst.critical('Users still access: {}'.format(self.access_users))
                time.sleep(5)
            if self.log_inst: self.log_inst.critical('No running access.')


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Reboot AP I/O Stress Test on Kamino Device. ***
        Examples: ./run.sh ap_reboot_io_stress.py --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-app', '--ap_power_port', help='AP port on power switch', metavar='PORT', type=int)
    parser.add_argument('-t', '--test_type', help="", default='m', choices=['u', 'd', 'm'])
    parser.add_argument('-un', '--user_number', help='How many users to do IO parallelly', type=int, default=1)
    parser.add_argument('-ipu', '--iteration_per_user', help='How many iterations the user will upload/download data', type=int, default=100)
    parser.add_argument('--file_server', help='File server IP address', default='fileserver.hgst.com')
    parser.add_argument('--private_network', action='store_true', default=False,
                        help='The test is running in private network or not')

    test = APRebootIOTest(parser)
    if test.main():
        sys.exit(0)
    sys.exit(1)
