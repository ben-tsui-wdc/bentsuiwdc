"""
author          :Nick yang <nick.yang@wdc.com>
last modified   :Ben Tsui <ben.tsui@wdc.com>
date            :2016/12/23
"""

import argparse
import requests
import time
import threading
import json

from platform_libraries.restAPI import RestAPI
from platform_libraries.adblib import ADB
from platform_libraries import common_utils


class ConcurrentStressSharing(object):

    TEST_SUITE = 'Sharing_Stress_Tests'
    TEST_NAME = 'Concurrent_Sharing_Access'

    def __init__(self):
        # Create usages
        example1 = '\n  python.exe concurrentSharing.py --uut_ip 192.168.1.110 --port 5555 --time 10'
        parser = argparse.ArgumentParser(description='*** Stress Test for sharing on Kamino (5 users concurrent) ***\n\nExamples:{0}'.format(example1),formatter_class=argparse.RawTextHelpFormatter)
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
        self.log.info('Step 1: Create 5 users on server and get access tokens for each user, finally attach them to device')
        user_id_lists = []
        worker = []
        user_list = {}
        for i in range(5):
            user_name = 'wdctest_stress_sharing_access_{0}+qawdc@test.com'.format(i)
            user_list["rest_u{}".format(i+1)] = RestAPI(uut_ip=self.uut_ip, env=self.env, username=user_name, password='Test1234')
            user_id = str(user_list["rest_u{}".format(i+1)].get_user_id())
            user_id_lists.append(user_id)
            self.log.debug('User id of wdctest_stress_sharing_access_{0} is {1}'.format(i, user_id_lists[i]))

        self.log.info('Step 2: User1 upload a file onto NAS')
        user_list['rest_u1'].upload_data(data_name='hello.txt', file_content='Hello!')
        self.log.info('Step 3: User1 creates Readfile permission for everyone')
        file_id_list, page_token = user_list['rest_u1'].get_data_id_list(type='file')
        file_id = str(file_id_list['hello.txt'])
        self.log.debug('File id of the uploaded file is {0}'.format(file_id))
        user_list['rest_u1'].set_permission(file_id, user_id='anybody', permission="ReadFile")
        if self.env == 'prod':
            self.log.info('Step 4a: Skip this step since Prod server does not support private sharing')
        else:
            self.log.info('Step 4a: User1 creates a new share record for other 4 users (Create a private share)')
            share_id = user_list['rest_u1'].create_shares(user_id_lists[0], [user_id_lists[0], user_id_lists[1],
                                                          user_id_lists[2], user_id_lists[3], user_id_lists[4]], file_id)
            self.log.debug('The private share ID is {0}'.format(share_id))
            self.log.info('Step 4b: User1 creates a new share record for anybody (Create a public share)')

        share_id2 = user_list['rest_u1'].create_shares(user_id_lists[0], 'anybody', file_id)
        self.log.debug('The public share ID is {0}'.format(share_id2))
        self.log.info('Step 5: Keep getting public/private share API in {0} minutes'.format(self.timeout))
        start = time.time()
        upload_log_time = start

        if self.timeout:
            timeout = int(self.timeout) * 60

            def _get_share(user, share_id):
                result = user.get_shares(share_id)
                if result:
                    self.count_passed += 1
                else:
                    self.count_failed += 1

            while (time.time() - start) < timeout:
                try:
                    for i in range(0, 5):
                        if self.env != 'prod':
                            self.log.info('*** Getting the share API from the created share by user1 (Get private share API testing) ***')
                            t = threading.Thread(name='GetPrivateShare%s' % i, target=_get_share, args=(user_list["rest_u{}".format(i+1)], share_id))
                            worker.append(t)

                        self.log.info('*** Getting the share API from the created share by user1 (Get public share API testing) ***')
                        w = threading.Thread(name='GetPublicShare%s' % i, target=_get_share, args=(user_list["rest_u{}".format(i+1)], share_id2))
                        worker.append(w)
                        if self.env != 'prod':
                            t.start()
                        w.start()
                    # Let the thread jobs all done
                    for wp in worker:
                        wp.join()

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

test = ConcurrentStressSharing()
test.run()
