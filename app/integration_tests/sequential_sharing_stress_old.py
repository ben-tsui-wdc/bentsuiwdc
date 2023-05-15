"""
author          :Nick yang <nick.yang@wdc.com>
last modified   :Ben Tsui <ben.tsui@wdc.com>
date            :2016/12/23
"""

import argparse
import requests
import time
import json

from platform_libraries.restAPI import RestAPI
from platform_libraries.adblib import ADB
from platform_libraries import common_utils


class SequentialStressSharing(object):

    TEST_SUITE = 'Sharing_Stress_Tests'
    TEST_NAME = 'Sequential_Sharing_Access'

    def __init__(self):
        # Create usages
        example1 = '\n  python.exe sequentialStressSharing.py --uut_ip 192.168.1.110 --port 5555 --time 10'
        parser = argparse.ArgumentParser(description='*** Stress Test for sharing on Kamino Android ***\n\nExamples:{0}'.format(example1), formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument('--uut_ip', help='Destination NAS IP address, ex. 192.168.1.45')
        parser.add_argument('--port', help='Destination IP port, ex. 5555')
        parser.add_argument('--time', help='Total testing duration (Minutes)', metavar='timeout', default='60')
        parser.add_argument('--env', help='Cloud test environment', default='dev1', choices=['dev1', 'qa1', 'prod'])
        parser.add_argument('--adb_server', help='Use adb server to run tests or not', action='store_true', default=False)
        parser.add_argument('--adb_server_ip', help='The IP address of adb server', default='10.10.10.10')
        parser.add_argument('--adb_server_port', help='The port of adb server', default='5037')
        parser.add_argument('--logstash', help='Logstash server IP address', default='10.92.234.101')
        parser.add_argument('--dry_run', help='Test mode, will not upload result to logstash', action='store_true', default=False)
        parser.add_argument('-ap_ssid', '--ap_ssid', help='The SSID of destination AP', metavar='SSID', default=None)
        parser.add_argument('-ap_password', '--ap_password', help='The password of destination AP', metavar='PWD', default=None)
        args = parser.parse_args()

        self.uut_ip = args.uut_ip
        self.port = args.port
        self.timeout = args.time
        self.env = args.env
        self.logstash_server = 'http://{}:8000'.format(args.logstash)
        self.log = common_utils.create_logger()
        self.dry_run = args.dry_run
        if args.adb_server:
            self.adb = ADB(adbServer=args.adb_server_ip, adbServerPort=args.adb_server_port, uut_ip=self.uut_ip)
        else:
            self.adb = ADB(uut_ip=args.uut_ip)

        self.adb.connect()
        self.product=self.adb.getModel()
        self.adb.stop_otaclient()
        self.build = ''
        self.count_passed = 0
        self.count_failed = 0
        self.total_passed = 0
        self.total_failed = 0

    def run(self):
        self.log.info('Step 1: Create a user1 on server')
        rest_u1 = RestAPI(uut_ip=self.uut_ip, env=self.env, username='wdctest_stress_sharing_access_0@test.com', password='Test1234')
        self.log.info('Step 2: User1 upload a file onto NAS')
        rest_u1.upload_data(data_name='hello.txt', file_content='Hello!')
        self.log.info('Step 3: User1 creates Readfile permission for everyone')
        user_id = str(rest_u1.get_user_id())
        self.log.debug('User id of user1 is {0}'.format(user_id))
        file_id_list, page_token = rest_u1.get_data_id_list(type='file')
        file_id = str(file_id_list['hello.txt'])
        self.log.debug('File id of the uploaded file is {0}'.format(file_id))
        rest_u1.set_permission(file_id, user_id='anybody', permission="ReadFile")
        self.log.info('Step 4: Create a user2 on server')
        rest_u2 = RestAPI(uut_ip=self.uut_ip, env=self.env, username='wdctest_stress_sharing_access_1@test.com', password='Test1234')
        # Test to upload file share record to the cloud
        if self.env == 'prod':
            self.log.info('Step 5a: Skip this step since Prod server does not support private sharing')
        else:
            self.log.info('Step 5a: User1 creates a new share record for User2 (Create a private share)')
            user_id2 = str(rest_u2.get_user_id())
            self.log.debug('User id of user2 is {0}'.format(user_id2))
            share_id = rest_u1.create_shares(user_id, [user_id, user_id2], file_id)
            self.log.debug('Private share ID: {}'.format(share_id))

        self.log.info('Step 5b: User1 creates a new share record for anybody (Create a public share)')
        share_id2 = rest_u1.create_shares(user_id, 'anybody', file_id)
        self.log.debug('The public share ID is {0}'.format(share_id2))
        self.log.info('Step 6: Keep getting public/private share API in {0} minutes'.format(self.timeout))
        start = time.time()
        upload_log_time = start

        if self.timeout:
            timeout = int(self.timeout) * 60
            while (time.time() - start) < timeout:
                try:
                    if self.env != 'prod':
                        self.log.info('*** Getting the share API from the created share by user1 (Get private share API testing) ***')
                        result = rest_u2.get_shares(share_id)
                        if result:
                            self.count_passed += 1
                        else:
                            self.count_failed += 1

                    self.log.info('*** Getting the share API from the created share by user1 (Get public share API testing) ***')
                    result = rest_u2.get_shares(share_id2)
                    if result:
                        self.count_passed += 1
                    else:
                        self.count_failed += 1
                except Exception as e:
                    self.log.warning("Stress sharing access test failed by exception, error message: {}".format(e.message))
                    self.count_failed += 1
                finally:
                    if time.time() - upload_log_time > 1800:
                        # Show & upload result every 1800 secs
                        self.build = self.adb.getFirmwareVersion()
                        self.log.info("Running on firmware version: {}".format(self.build))
                        if not self.dry_run:
                            self._upload_result()
                        self._show_current_result()
                        upload_log_time = time.time()

            if self.count_passed != 0 or self.count_failed != 0:
                self.build = self.adb.getFirmwareVersion()
                self.log.info("Running on firmware version: {}".format(self.build))
                if not self.dry_run:
                    self._upload_result()
                self._show_current_result()

    def _show_current_result(self):
        self.log.info('### Share access results in last 30 mins ###')
        self.log.info('Passed: {} times'.format(self.count_passed))
        self.log.info('Failed: {} times'.format(self.count_failed))
        self.total_passed += self.count_passed
        self.total_failed += self.count_failed
        self.count_passed = 0
        self.count_failed = 0
        self.log.info('### Total share access results ###')
        self.log.info('Passed: {} times'.format(self.total_passed))
        self.log.info('Failed: {} times'.format(self.total_failed))

    def _upload_result(self):
        headers = {'Content-Type': 'application/json'}
        data = {'testSuite': self.TEST_SUITE,
                'testName': self.TEST_NAME,
                'build': self.build,
                'shareAccessPassed': int(self.count_passed),
                'shareAccessFailed': int(self.count_failed),
                'product': self.product}

        response = requests.post(url=self.logstash_server, data=json.dumps(data), headers=headers)
        if response.status_code == 200:
            self.log.info('Uploaded JSON results to logstash server {}'.format(self.logstash_server))
        else:
            error_message = 'Upload to logstash server {0} failed, {1}, error message: {2}'.\
                             format(self.logstash_server, response.status_code, response.content)
            self.log.error(error_message)
            raise Exception(error_message)

test = SequentialStressSharing()
test.run()
