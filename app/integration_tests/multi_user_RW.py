___author___ = 'Jason Chiang <jason.chiang@wdc.com>'

import argparse
import os
import random
import re
import subprocess
import sys
import time
from threading import Thread

from platform_libraries import common_utils
from platform_libraries.restAPI import RestAPI
from platform_libraries.adblib import ADB


class multi_user_RW():
    def __init__(self, uut_ip=None, env=None, username=None, password=None):
        self.uut_ip = uut_ip
        self.env = env
        self.username = username
        self.password = password
        self.adb = ADB(uut_ip=uut_ip)
        self.adb.connect()
        self.log = common_utils.create_logger(root_log='multi_user_RW')
        self.REST_API = RestAPI(self.uut_ip, self.env, self.username, self.password, root_log='multi_user_RW_REST_API')
        self.user_id = self.REST_API.get_user_id()
        self.test_file = self.user_id.replace('|', '_')
        self.root_folder = '/data/wd/diskVolume0/restsdk/userRoots/'
        self.errorflag = False  # If errorflag is True, the process will be stopped.


    # The basic unit of file_size is "512 bytes", namely 0.5KB. 
    def _create_random_file(self):
        self.log.info("{0} -> Creating file: {1}...".format(self.username, self.user_id.replace('|', '_')))
        try:
            result = subprocess.call('dd if=/dev/urandom of={0} count={1}'.format(self.test_file, 40960), shell=True)
        except Exception as e:
            self.log.error("{0} -> Failed to create file: {1}, error message: {2}".format(self.username, self.test_file, repr(e)))
            self.errorflag = True
            sys.exit(1)


    def _md5_checksum(self, file_path=None):
        if file_path == 'local':
            process = subprocess.Popen('md5sum {}'.format(self.test_file), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)  # Merge the stderr into stdout.
            stdout = process.communicate()[0]  # By the way, communicate()[1] is stderr.
            return stdout.split()[0]
        elif file_path == 'remote':
            file_path = os.path.join(self.root_folder, "'{}'".format(self.user_id))
            result = self.adb.executeShellCommand('md5sum {0}/{1}'.format(file_path, self.test_file), timeout=600)
            if 'No such file or directory' in result[0]:
                self.log.error("{0} -> The tested file: {1}/{2} disappeared !".format(self.username, file_path, self.test_file))
                self.errorflag = True
                sys.exit(1)
            else:
                result = result[0].strip().split()[0]
                return result


    def _delete_file(self):
        '''
        If the script is executed the first time or the user is ever detached, there is no tested file in personal userRoots.
        Therefore, use "try except" to avoid that the script will stop due to RaiseError.
        '''
        try:
            data_id = self.REST_API.get_data_id_list(type='file', data_name=self.test_file)
            self.REST_API.delete_file(data_id)
        except:
            pass


    def _upload_data(self):
        try:
            with open(self.test_file, 'rb') as f:
                read_data = f.read()
                self.log.info("{0} -> Start uploading file to test device...".format(self.username))
                self.REST_API.upload_data(data_name=self.test_file, file_content=read_data, suffix=self.test_file)
                self.log.info("{0} -> Upload file completed.".format(self.username))
        except Exception as e:
            self.log.error("{0} -> _upload_data({1}):{2}".format(self.username, self.test_file, repr(e)))
            self.errorflag = True
            sys.exit(1)


    def _download_file(self):
        try:
            data_id = self.REST_API.get_data_id_list(type='file', data_name=self.test_file)
        except:
            self.errorflag = True
            raise
        try:
            self.log.info("{0} -> Start downloading file from test device...".format(self.username))
            content = self.REST_API.get_file_content_v3(data_id).content
            with open(self.test_file, 'wb') as f:
                f.write(content)
        except Exception as e:
            self.log.error("{0} -> _download_file({1}):{2}".format(self.username, self.test_file, repr(e)))
            self.errorflag = True
            sys.exit(1)


    def run(self, owner, test_time):
        
        start_time = time.time()

        while time.time() - start_time < test_time:
            if self.errorflag == True:
                sys.exit(1)

            case = random.randint(1,3)
            
            # User uploads and downloads file.
            if case == 1:
                self.log.info("{0} -> Case 1 :User uploads and downloads file.".format(self.username))
                self._create_random_file()  # successful
                checksum_original = self._md5_checksum(file_path='local')

                self._delete_file()

                self._upload_data()

                checksum_upload = self._md5_checksum(file_path='remote')  # DUT: Device Under Test.
                if checksum_upload != checksum_original:
                    self.log.error('user({0}) -> md5checksum of test_file({1}) failed after uploading to DUT!'.format(self.username, self.test_file))
                    self.errorflag = True
                    sys.exit(1)

                # Delete the local file before downloading file from remote DUT. 
                process = subprocess.Popen('rm -f {}'.format(self.test_file), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)  # Merge the stderr into stdout.
                
                self._download_file()
                
                checksum_download = self._md5_checksum(file_path='local')
                if checksum_download != checksum_original:
                    self.log.error('user({0}) -> md5checksum of test_file({1}) failed after downloading from DUT!'.format(self.username, self.test_file))
                    self.errorflag = True
                    sys.exit(1)

                self.log.info("{0} -> Case 1 (uploads and downloads file): finished successfully".format(self.username))

            # User is detached by himself, then attached user to DUT back.
            elif case == 2:
                self.log.info("{0} -> Case 2 :User detaches himself, then attached user to DUT back.".format(self.username))
                try:
                    if self.REST_API.detach_user_from_device(user_id=self.user_id, id_token=self.REST_API.get_id_token()) == 200:
                        self.log.info("{0} -> Case 2 (User is detached by himself): finished successfully.".format(self.username))
                    else:
                        self.errorflag = True
                        self.log.error("{0} -> Case 2 (User is detached by himself): failed.".format(self.username))
                        sys.exit(1)
                    self.REST_API = RestAPI(self.uut_ip, self.env, self.username, self.password, root_log='multi_user_RW_REST_API')
                except:
                    self.errorflag = True
                    raise

            # User is detached by owner, then attaches user to DUT back.
            elif case == 3:
                #time.sleep(0.5)
                try:
                    self.log.info("{0} -> Case 3 :Owner detaches user, then attaches user to DUT back.".format(self.username))
                    if self.REST_API.detach_user_from_device(user_id=self.user_id, id_token=owner.REST_API.get_id_token()) == 200:
                        self.log.info("{0} -> Case 3 (User is detached by owner):finished successfully.".format(self.username))
                    else:
                        self.errorflag = True
                        self.log.error("{0} -> Case 3 (User is detached by owner):failed.".format(self.username))
                        sys.exit(1)
                    self.REST_API = RestAPI(self.uut_ip, self.env, self.username, self.password, root_log='multi_user_RW_REST_API')
                except:
                    self.errorflag = True
                    raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='USB Slurp Performance KPI test\nExample:{}'.format('\n'))
    parser.add_argument('--uut_ip', help='Test device IP address')
    parser.add_argument('--env', help='Cloud test environment', default='dev1', choices=['dev1', 'qa1', 'prod'])
    parser.add_argument('--test_time', help='Total tested duration time, by default is 300 seconds.', default='300' )
    parser.add_argument('--total_user', help='The number of general users, by default is 5 users(excluding owner).', default='5' )
    parser.add_argument('--port', help='Destination port number', default='5555' )
    parser.add_argument('--user', help='The username of owner attached in test device', default='multi_user_RW{}+qawdc@test.com')
    parser.add_argument('--pw', help='The password of owner attached in test device', default='Test1234')
    args = parser.parse_args()
    uut_ip = args.uut_ip
    env = args.env
    test_time = int(args.test_time)
    total_user = int(args.total_user) + 1  # total user = general users and one owner
    user = args.user
    pw = args.pw

    user_dict = {}
    for i in xrange(total_user):
        time.sleep(0.5)
        user_dict.update({'user{}'.format(i):multi_user_RW(uut_ip=uut_ip, env=env, username=user.format(i), password=pw)})    


    print '\n\n multi_user_RW stress START! \n\n'
    thread_list =[]
    for i in xrange(1, total_user):  # Exclude owner
        t = Thread(target=user_dict.get('user{}'.format(i)).run, args=(user_dict.get('user0'), test_time))
        thread_list.append(t)
        t.start()

    main_thread_errorflag = False
    start_time = time.time()
    while time.time() - start_time < test_time:
        for element in user_dict:
            if user_dict.get(element).errorflag == True:
                main_thread_errorflag = True
                for element in user_dict:
                    user_dict.get(element).errorflag = True
        if main_thread_errorflag == True:
            break
        time.sleep(1)

    time.sleep(10)
    if main_thread_errorflag:
        print '\n\nmulti_user_RW Failed \n\n'
    else:
        print '\n\nmulti_user_RW SUCCESS\n\n'