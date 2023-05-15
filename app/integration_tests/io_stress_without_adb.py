# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import os
import shutil
import random
import time

from uuid import uuid4
from multiprocessing import Process, Queue

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.compare import compare_images
from platform_libraries.pyutils import save_to_file
from platform_libraries.restAPI import RestAPI
from platform_libraries.sql_client import ThumbnailsDatabase
from transcoding_tests.functional_tests.single_file_transcoding import SingleFileTranscodingTest


class StressIOTest(TestCase):

    SETTINGS = {
        'adb': False,
        'power_switch': False,
    }

    TEST_SUITE = 'Stress_IO_Test'
    TEST_NAME = 'Stress_IO_Test'
    TEST_JIRA_ID = 'KAM-17192'
    POOL_SIZE = 4  # Use for multiprocessing Pool
    LOCAL_THUMB_FOLDER = os.path.join(os.getcwd(), 'stressio_thumbs')
    LOCAL_UPLOAD_FOLDER = os.path.join(os.getcwd(), 'stressio_upload')
    LOCAL_DOWNLOAD_FOLDER = os.path.join(os.getcwd(), 'stressio_download')
    NAS_ROOT_FOLDER = '/data/wd/diskVolume0/restsdk/userRoots/'
    NAS_UPLOAD_FOLDER = 'data_uploaded'  # Use for upload case, files uploads from local to here
    NAS_DOWNLOAD_FOLDER = 'data_for_download'  # Use for download case, file will be download from here to local client
    NAS_DOWNLOAD_FOLDER_ID = ''
    THUMB_DB_PATH = os.path.join(os.getcwd(), 'stressio_thumbs/thumbs.db')
    USER_LIST = []
    USER_ID_LIST = []
    TOTAL_PASSED = 0
    TOTAL_FAILED = 0
    # Use for calculating the average elapsed time for each iteration
    UPLOAD_ITERATION_LIST = []
    DOWNLOAD_ITERATION_LIST = []

    def declare(self):
        self.file_server_path = '/test/IOStress/'
        self.thumbnail_server_path = '/test/thumbnails/IOStress/'
        self.disable_barrier = False

    def init(self):
        # Todo: change default owner name -> not wdc_owner@test.com
        self.USER_LIST = [self.uut_owner]  # We will have at least 1 user (device owner)
        self.USER_ID_LIST = [str(self.uut_owner.get_user_id())]

    def before_loop(self):
        pass

    def before_test(self):
        self.FILE_LIST = []
        self.FILE_DOWNLOAD_ID_LIST = []
        self.FILE_MD5_LIST = []

        self.log.info('[ Run before_test step ]')
        #self.adb.stop_otaclient()

        # Todo: Why this is not working?

        '''
        def _collect_user_object(user):
            print "collect:", user
            self.user_list.append(user)

        def _create_user(test_user_name):
            print test_user_name
            user = RestAPI(self.env.uut_ip, self.env.cloud_env, test_user_name, self.env.password)
            return user

        self.log.info("Preparing users")
        # Use multiprocess to create users. The user_number - 1 since we already have a device owner
        pool = Pool(self.POOL_SIZE)
        for user_id in range(int(self.user_number) - 1):
            test_user_name = 'wdctest_stressio_{}@test.com'.format(user_id + 1)
            print test_user_name
            pool.apply_async(_create_user, args=(test_user_name, ), callback=_collect_user_object)

        print self.user_list

        pool.close()
        pool.join()
        '''

        self.log.info("### Step 1: Create users and attach them in UUT device ###")

        if self.user_number > 1:
            if self.test_type == 'mt':
                # If test_type=='mix+transcoding', the uut_owner will only execute transcoding rather than upload/download.
                # That means the actual number of users which executing upload/downlaod is one less.
                self.user_number += 1

            for user_id in range(int(self.user_number) - 1):
                user = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env, username='{}_{}+qawdc@test.com'.format(self.test_user_name, user_id+1), password='Wdctest1234', init_session=False)
                if self.env.cloud_env == 'prod':
                    self.log.warning('Env is {}, skipped the wait cloud connected check ...'.format(self.env.cloud_env))
                    with_cloud_connected = False
                else:
                    with_cloud_connected = True
                #user.set_adb_client(self.adb)
                user.init_session(client_settings={'config_url': self.uut['config_url']}, with_cloud_connected=with_cloud_connected)

                self.USER_LIST.append(user)
                self.USER_ID_LIST.append(user.get_user_id())

        self.log.info("### Step 2: Prepare local test folders ###")
        self.log.info("Create upload folder")
        if os.path.exists(self.LOCAL_UPLOAD_FOLDER):
            shutil.rmtree(self.LOCAL_UPLOAD_FOLDER)
        os.mkdir(self.LOCAL_UPLOAD_FOLDER)

        self.log.info("Download thumbnails files from file server")
        download_path = '{0}{1}'.format('http://{}'.format(self.file_server), self.thumbnail_server_path)
        cur_dir = self.thumbnail_server_path.count('/')
        url = 'wget -np --no-host-directories --cut-dirs={0} -r {1} -P {2} --no-verbose'.format(cur_dir, download_path, self.LOCAL_THUMB_FOLDER)
        if self.private_network:
            url += ' --no-passive'
        os.popen(url)

        self.log.info("Download test files from file server to upload folder")
        download_path = '{0}{1}'.format('http://{}'.format(self.file_server), self.file_server_path)
        cur_dir = self.file_server_path.count('/')
        url = 'wget -np --no-host-directories --cut-dirs={0} -r {1} -P {2} --no-verbose'.format(cur_dir, download_path, self.LOCAL_UPLOAD_FOLDER)
        if self.private_network:
            url += ' --no-passive'
        os.popen(url)

        for (dirpath, dirnames, filenames) in os.walk(self.LOCAL_UPLOAD_FOLDER):
            self.FILE_LIST.extend(filenames)
            break

        self.log.info("Create download folder")
        if os.path.exists(self.LOCAL_DOWNLOAD_FOLDER):
            shutil.rmtree(self.LOCAL_DOWNLOAD_FOLDER)
        os.mkdir(self.LOCAL_DOWNLOAD_FOLDER)

        self.log.info("Create download sub folder for each user")
        for user_id in range(int(self.user_number)):
            local_folder_name = os.path.join(self.LOCAL_DOWNLOAD_FOLDER, 'user_{}'.format(user_id))
            os.mkdir(local_folder_name)

        self.log.info("Local test folders are ready")

        self.log.info("### Step 3: Prepare UUT test folders ###")
        self.log.info("Upload test files into owner's folder for download test case")
        self.USER_LIST[0].commit_folder(folder_name=self.NAS_DOWNLOAD_FOLDER)
        self.NAS_DOWNLOAD_FOLDER_ID = self.USER_LIST[0].get_data_id_list(type='folder', data_name=self.NAS_DOWNLOAD_FOLDER)
        self.log.warning('nas_folder_id:{}'.format(self.NAS_DOWNLOAD_FOLDER_ID))
        self.USER_LIST[0].set_permission(self.NAS_DOWNLOAD_FOLDER_ID, user_id='anybody', permission="ReadFile")

        for index, file in enumerate(self.FILE_LIST):
            with open(os.path.join(self.LOCAL_UPLOAD_FOLDER, file), 'rb') as f:
                #self.log.info("Uploading file: {0} into test folder {1}".format(file, self.NAS_DOWNLOAD_FOLDER))
                self.USER_LIST[0].chuck_upload_file(file_object=f, file_name=file, parent_folder=self.NAS_DOWNLOAD_FOLDER)
            file_id = self.USER_LIST[0].get_data_id_list(type='file', parent_id=self.NAS_DOWNLOAD_FOLDER_ID, data_name=file)
            # Todo: (1/3) find how to share data and let the other user use their id to get owner's file
            # self.USER_LIST[0].set_permission(file_id, user_id='anybody', permission="ReadFile")
            self.FILE_DOWNLOAD_ID_LIST.append(file_id)
            self.log.info("Debug: uploading file name:{} into test folder {}; file_id:{}".format(file, self.NAS_DOWNLOAD_FOLDER, file_id))
            #print "Debug: uploading file name:{}, file_id:{}".format(file, file_id)  # For debug 404 Not found issue
        # Todo: (2/3) find how to share data and let the other user use their id to get owner's file
        # self.USER_LIST[0].create_shares(self.USER_ID_LIST[0], self.USER_ID_LIST, self.FILE_DOWNLOAD_ID_LIST)

        if self.disable_barrier:
            self.log.warning("Try to close the barrier due to Jira ticket: KAM200-605")
            self.adb.executeShellCommand('mount -o remount,barrier=0 /data/wd/diskVolume0', consoleOutput=True)
            
        self.log.info("### Prepare environment finished ###")

    def test(self):

        def _upload(user_num):
            test_passed = True
            test_exc_info = None
            user_id = self.USER_ID_LIST[user_num].replace('auth0|', 'auth0\|')
            uploaded_file_dict = dict()
            self.log.info("Create a folder: {} for User{} to upload files".format(self.NAS_UPLOAD_FOLDER, user_num))
            self.USER_LIST[user_num].commit_folder(folder_name=self.NAS_UPLOAD_FOLDER)
            folder_id = self.USER_LIST[user_num].get_data_id_list(type='folder', data_name=self.NAS_UPLOAD_FOLDER)
            self.log.warning("upload_folder_id: {}".format(folder_id))
            try:
                for index, file in enumerate(self.FILE_LIST):
                    with open(os.path.join(self.LOCAL_UPLOAD_FOLDER, file), 'rb') as f:
                        # self.log.info("### User{0}: Upload file: {1} ###".format(user_num, file))
                        upload_start_time = time.time()
                        self.USER_LIST[user_num].chuck_upload_file(file_object=f, file_name=file, parent_id=folder_id)
                        upload_elapsed_time = time.time() - upload_start_time
                        self.log.info("### User{0}: Upload file: {1} complete. Time elapsed: {2} ###".format(user_num, file, upload_elapsed_time))

                    # File comparison.
                    #checksum = _uut_md5_checksum(os.path.join(self.NAS_ROOT_FOLDER, user_id, self.NAS_UPLOAD_FOLDER, file))
                    #result = _compare_md5_checksum(user_num, file, self.FILE_MD5_LIST[index], checksum)
                    #if not result:
                    #    test_passed = False

                    file_id = self.USER_LIST[user_num].get_data_id_list(type='file', data_name=file, parent_id=folder_id)
                    uploaded_file_dict[file] = file_id

                    # Thumbnail comparison.
                    result = _thumbnail_comparison(user_num, file_id, file)
                    if not result:
                        test_passed = False

                """ Delete the whole folder instead of one by one since 2018/07/05
                for file_name, file_id in uploaded_file_dict.iteritems():
                    delete_start_time = time.time()
                    result = self.USER_LIST[user_num].delete_file(file_id)
                    delete_elapsed_time = time.time() - delete_start_time
                    if result:
                        self.log.info("### User{0}: Delete file: {1} complete. Elapsed time: {2}".format(user_num, file_name, delete_elapsed_time))
                    else:
                        self.log.error("### User{0}: Delete file: {1} with id: {2} failed! ###".format(user_num, file_name, file_id))
                """
                if user_num == 0:
                    owner = True
                else:
                    owner = False

                delete_start_time = time.time()
                result = self.USER_LIST[user_num].delete_file(folder_id, as_owner=owner)
                delete_elapsed_time = time.time() - delete_start_time
                if result:
                    self.log.info("### User{0}: Delete folder: {1} complete. Elapsed time: {2}".
                                  format(user_num, folder_id, delete_elapsed_time))
                else:
                    self.log.error("### User{0}: Delete folder: {1} with id: {2} failed! ###".
                                   format(user_num, folder_id, file_id))

            except Exception as e:
                self.log.error("### User{0}: Failed to upload file, error message: {1} ###".format(user_num, repr(e)), exc_info=True)
                test_passed = False
                test_exc_info = sys.exc_info()

            return test_passed, test_exc_info

        def _download(user_num):
            test_passed = True
            test_exc_info = None
            try:
                for index, file in enumerate(self.FILE_LIST):
                    # self.log.info("### User{0}: Download file: {1} ###".format(user_num, file))
                    # Todo: (3/3) find how to share data and let the other user use their id to get owner's file
                    # content, elapsed = self.USER_LIST[index].get_file_content(self.FILE_DOWNLOAD_ID_LIST[index])
                    download_start_time = time.time()
                    content = self.USER_LIST[0].get_file_content_v3(self.FILE_DOWNLOAD_ID_LIST[index]).content
                    with open(os.path.join(self.LOCAL_DOWNLOAD_FOLDER, 'user_{}'.format(user_num), file), 'wb') as f:
                        f.write(content)
                    download_elapsed_time = time.time() - download_start_time
                    self.log.info("### User{0}: Download file: {1} complete. Time elapsed: {2} ###".format(user_num, file, download_elapsed_time))
                    checksum = _local_md5_checksum(os.path.join(self.LOCAL_DOWNLOAD_FOLDER, 'user_{}'.format(user_num), file))
                    result = _compare_md5_checksum(user_num, file, self.FILE_MD5_LIST[index], checksum)
                    if not result:
                        test_passed = False
            except Exception as e:
                self.log.error("### User{0}: Failed to download file, error message: {1} ###".format(user_num, repr(e)))
                test_passed = False
                test_exc_info = sys.exc_info()

            for file in self.FILE_LIST:
                try:
                    os.remove(os.path.join(self.LOCAL_DOWNLOAD_FOLDER, 'user_{}'.format(user_num), file))
                except Exception as e:
                    self.log.error("### User{}: Failed to remove file({}) in client, error message: {} ###".format(user_num, file, repr(e)))
                    test_passed = False

            return test_passed, test_exc_info

        def _local_md5_checksum(path):
            response = os.popen('md5sum {}'.format(path))
            if response:
                result = response.read().strip().split()[0]
                return result
            else:
                self.log.error("There's no response from local md5 checksum")
                return None

        def _uut_md5_checksum(path):
            response = self.adb.executeShellCommand('busybox md5sum {}'.format(path), consoleOutput=False)
            if response:
                result = response[0].strip().split()[0]
                return result
            else:
                self.log.error("There's no response from uut md5 checksum")
                return None

        def _compare_md5_checksum(user_num, file, before, after):
            if before == after:
                return True
            else:
                self.log.error('### User{0}: {1} md5 comparison failed! md5_before: {2}, md5_after: {3} ###'.format(user_num, file, before, after))
                return False

        def _thumbnail_comparison(user_num, file_id, file):
            try:
                local_thumb_path = _get_local_thumb_path(file)
                if not local_thumb_path: # Thumbnail not support.
                    return True
                # Download thumbnail.
                start_time = time.time()
                restsdk_thumb_path = _get_restsdk_thumb_path(user_num, file_id)
                download_elapsed_time = time.time() - start_time
                self.log.info("### User{0}: Get file thumbnail: {1} complete. Time elapsed: {2} ###".format(user_num, file, download_elapsed_time))
                if not restsdk_thumb_path:
                    self.log.error('### User{0}: {1} thumbnail download failed! ###'.format(user_num, file))
                    return False
                # Compare image.
                keep_thumb = False
                result = compare_images(local_thumb_path, restsdk_thumb_path, threshold=0.05, log_inst=self.log)
                if not result:
                    self.log.error('### User{0}: {1} thumbnail comparison failed! ###'.format(user_num, file))
                    keep_thumb = True
                    return False
                return True
            finally:
                if 'restsdk_thumb_path' in locals() and os.path.exists(restsdk_thumb_path):
                    if keep_thumb:
                        save_path = os.path.join(self.env.output_folder, uuid4().hex+'.jpg')
                        self.log.warning('### User{0}: {1} thumbnail move to {2} for tracing ###'.format(user_num, file, save_path))
                        os.rename(restsdk_thumb_path, save_path)
                    else: # Delete downloaded thumb.
                        os.remove(restsdk_thumb_path)

        def _get_local_thumb_path(file):
            with ThumbnailsDatabase(db_file=self.THUMB_DB_PATH) as db_client:
                sub_path = db_client.get_file_by_name(filename=file, size='200c')
                if not sub_path:
                    return None
                return os.path.join(self.LOCAL_THUMB_FOLDER, sub_path)

        def _get_restsdk_thumb_path(user_num, file_id):
            try:
                tmp_path = os.path.join(self.LOCAL_DOWNLOAD_FOLDER, '_thumb{}.jpg'.format(user_num))
                response = self.USER_LIST[user_num].get_file_content_v3(file_id, size='200c', temp_size_max=50)
                save_to_file(iter_obj=response.iter_content(chunk_size=1024), file_name=tmp_path)
                return tmp_path
            except Exception as e:
                self.log.exception(str(e))
                return None

        def _get_md5_checksum_standard():
            self.FILE_MD5_LIST = []
            # Get the md5 checksum list for comparison standard
            for file in self.FILE_LIST:
                md5_before = _local_md5_checksum(os.path.join(self.LOCAL_UPLOAD_FOLDER, file))
                self.FILE_MD5_LIST.append(md5_before)

            if len(self.FILE_MD5_LIST) != len(self.FILE_LIST):
                error_msg = 'Some of the md5 checksum is missing, stop the test'
                self.log.error(error_msg)
                raise RuntimeError(error_msg)

        # This is for that sometimes calculating the checksum of testing files on Ubuntu will fail.
        for i in xrange(5):
            try:
                _get_md5_checksum_standard()
                break
            except RuntimeError as e:
                print 'number of fail={}'.format(i)
                print str(e)
                if i == 4:
                    raise

        def _select_test_type(queue, iteration, user_num, test_type):
            total_test_passed = 0
            total_test_failed = 0
            upload_list = []
            download_list = []
            for i in range(iteration):
                if test_type == 'mt':
                    if user_num == 0:  # That means this is owner.
                        type = 'tr'  # If test_type='mix+transcoding', uut_owner will only execute transcoding.
                    else:
                        # Because only one user can transcode at one time.
                        type = random.choice(['u', 'd'])  # Mixed type, randomly choose upload/download
                elif test_type == 'm':
                    type = random.choice(['u', 'd'])
                else:
                    type = test_type

                if type == 'd':
                    type_temp = 'Download'
                elif type == 'u':
                    type_temp = 'Upload' 
                elif type == 'tr':
                    type_temp = 'Transcoding'
                print '################ User{0}: iteration {1}, Type: {2} Start ###'.format(user_num, i+1, type_temp)
                self.log.info('### User{0}: iteration {1}, Type: {2} Start ###'.format(user_num, i+1, type_temp))
                iter_start_time = time.time()
                if type == 'd':
                    test_result, test_exc_info = _download(user_num)
                elif type == 'u':
                    test_result, test_exc_info = _upload(user_num)
                elif type == 'tr':
                    # transcoding
                    test_result, test_exc_info = self._transcoding()
                iter_elapsed_time = time.time() - iter_start_time
                self.log.info('### User{0}: iteration {1}, Type: {2} Complete, Elapsed Time: {3} ###'.
                              format(user_num, i+1, type_temp, iter_elapsed_time))

                if type == 'd':
                    download_list.append(iter_elapsed_time)
                elif type == 'u':
                    upload_list.append(iter_elapsed_time)

                if test_result:
                    total_test_passed += 1
                else:
                    total_test_failed += 1
                # Append the result for whole test
                if test_exc_info:
                    test_step_result = self.log.TestStep()
                    test_step_result["description"] = "io_stress"
                    test_step_result["messages"] = ["### User{}: iteration {}, Failed to {} ###".format(user_num, i+1, type_temp)]
                    test_step_result.set_exc_info(test_exc_info, overwrite=True)
                    self.log.append_test_step(test_step_result)


            queue.put([total_test_passed, total_test_failed, upload_list, download_list])

        self.log.info('[ Start testing ]')
        process_list = []
        queue_list = []
        for index in range(len(self.USER_LIST)):
            test_type = self.test_type
            queue = Queue()
            queue_list.append(queue)
            process = Process(target=_select_test_type, args=(queue_list[index], self.iteration_per_user, index, test_type, ))
            process.start()
            process_list.append(process)

        for index, process in enumerate(process_list):
            process.join()
            test_result = queue_list[index].get()
            self.TOTAL_PASSED += int(test_result[0])
            self.TOTAL_FAILED += int(test_result[1])
            self.UPLOAD_ITERATION_LIST += test_result[2]
            self.DOWNLOAD_ITERATION_LIST += test_result[3]
            
        self.log.info("Total Passed: {}".format(self.TOTAL_PASSED))
        self.log.info("Total Failed: {}".format(self.TOTAL_FAILED))        
        self.data.test_result['StressIOTestPassed'] = self.TOTAL_PASSED
        self.data.test_result['StressIOTestFailed'] = self.TOTAL_FAILED

        upload_num = len(self.UPLOAD_ITERATION_LIST)
        download_num = len(self.DOWNLOAD_ITERATION_LIST)
        self.log.info("Total Upload Iterations: {}".format(upload_num))
        self.log.info("Total Download Iterations: {}".format(download_num))

        if upload_num == 0:
            avg_upload_time = None
        else:
            avg_upload_time = sum(self.UPLOAD_ITERATION_LIST) / float(upload_num)

        if download_num == 0:
            avg_download_time = None
        else:
            avg_download_time = sum(self.DOWNLOAD_ITERATION_LIST) / float(download_num)

        self.log.info("Average Upload Time For Each Iteration: {}".format(avg_upload_time))
        self.log.info("Average Download Time For Each Iteration: {}".format(avg_download_time))

        if self.TOTAL_FAILED > 0:
            raise self.err.TestFailure('Test failed {} times in {} iterations!'.format(self.TOTAL_FAILED, self.TOTAL_PASSED + self.TOTAL_FAILED))


    def _transcoding(self):
        env_dict = self.env.dump_to_dict()
        #env_dict['Settings'] = ['uut_owner=False']
        env_dict['db_file_url'] = 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/mediainfo_db'
        # Should choose transcoding file at random
        env_dict['test_file_url'] = 'http://fileserver.hgst.com/test/VideoTranscoding/FunctionalTest/1080P_H.264.mp4'
        env_dict['target_container'] = 'matroska'
        env_dict['target_resolution'] = '720p'
        single_file_transcoding = SingleFileTranscodingTest(env_dict)
     

        """ Prepare test environment. """
        #if self.not_init_data:
        #    return
        #self.log.info("Clean UUT owner's home directory...")
        #self.uut_owner.clean_user_root()

        test_passed = True
        test_exc_info = None
        try:
            # Upload transcoding test data to device via RestSDK API.
            if single_file_transcoding.local_data_path:
                self.log.info("Upload test data from local to UUT owner's home directory...")
                self.uut_owner.recursive_upload(path=single_file_transcoding.local_data_path)
                self.log.info("Uploading is done.")
                # Execute transcoding 
                single_file_transcoding.test()
                # Delete the folder which is used for transcoding in device
                resp = self.USER_LIST[0].search_file_by_parent_and_name(single_file_transcoding.local_data_path)
                folder_id = resp[0].get('id')
                self.USER_LIST[0].delete_file(folder_id)
            else:
                self.log.warning("There is no single_file_transcoding.local_data_path.")
                test_passed = False
        except Exception as e:
            test_passed = False
            test_exc_info = sys.exc_info()

        return test_passed, test_exc_info


    def after_test(self):
        self.log.info('[ Run after_test step ]')
        self.log.info('Clean up the test environment')
        self.log.info('Removing local folders')
        shutil.rmtree(self.LOCAL_UPLOAD_FOLDER)
        shutil.rmtree(self.LOCAL_DOWNLOAD_FOLDER)
        self.log.info('Removing uut test folder')
        
        # Delete the folder for upload/dowload in device
        folder_id = self.USER_LIST[0].get_data_id_list(type='folder', data_name=self.NAS_DOWNLOAD_FOLDER)
        self.USER_LIST[0].delete_file(folder_id)


    def after_loop(self):
        pass

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Stress IO Test on Kamino Android ***
        Examples: ./run.sh  --uut_ip 10.136.137.159\
        """)
    parser.add_argument('-t', '--test_type', default='m', choices=['u', 'd', 'm', 'mt'], help='u:uplod, d:download, m:mix, mt:mix+transcoding')
    parser.add_argument('-tun', '--test_user_name', help='the user name for test', default='wdc_stressio')
    parser.add_argument('-un', '--user_number', help='How many users to do IO parallelly', type=int, default=5)
    parser.add_argument('-ipu', '--iteration_per_user', help='How many iterations the user will upload/download data', type=int, default=100)
    parser.add_argument('--file_server', help='File server IP address', default='fileserver.hgst.com')
    parser.add_argument('--private_network', action='store_true', default=False,
                        help='The test is running in private network or not')
    parser.add_argument('-fsp', '--file_server_path', help="Test folder path on file server", default='/test/IOStress/')
    parser.add_argument('-tsp', '--thumbnail_server_path', help="Test thumbnail folder path on file server", default='/test/thumbnails/IOStress/')
    parser.add_argument('--disable_barrier', '-ds', action='store_true', default=False, help='disable the barrier in test device')

    test = StressIOTest(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)