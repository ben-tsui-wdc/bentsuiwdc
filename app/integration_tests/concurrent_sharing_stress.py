# -*- coding: utf-8 -*-

__author_1__ = "Nick Yang <nick.yang@wdc.com>"
__author_2__ = "Ben Tsui <ben.tsui@wdc.com>"


# std modules
import json
import requests
import sys
import threading
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.restAPI import RestAPI


class ConcurrentSharingStress(TestCase):

    TEST_SUITE = 'Sharing_Stress_Tests'
    TEST_NAME = 'Concurrent_Sharing_Access'

    def before_test(self):
        self.count_passed = 0
        self.count_failed = 0
        self.total_passed = 0
        self.total_failed = 0


    def test(self):
        self.log.info('Step 1: Create 5 users on server and get access tokens for each user, finally attach them to device')
        user_id_lists = []
        worker = []
        user_list = {}
        for i in range(5):
            user_name = 'wdctest_stress_sharing_access_{0}+qawdc@test.com'.format(i)
            user_list["rest_u{}".format(i+1)] = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env, username=user_name, password='Test1234')
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
        if self.env.cloud_env == 'prod':
            self.log.info('Step 4a: Skip this step since Prod server does not support private sharing')
        else:
            self.log.info('Step 4a: User1 creates a new share record for other 4 users (Create a private share)')
            share_id = user_list['rest_u1'].create_shares(user_id_lists[0], [user_id_lists[0], user_id_lists[1],
                                                          user_id_lists[2], user_id_lists[3], user_id_lists[4]], file_id)
            self.log.debug('The private share ID is {0}'.format(share_id))
            self.log.info('Step 4b: User1 creates a new share record for anybody (Create a public share)')

        share_id2 = user_list['rest_u1'].create_shares(user_id_lists[0], 'anybody', file_id)
        self.log.debug('The public share ID is {0}'.format(share_id2))
        self.log.info('Step 5: Keep getting public/private share API in {0} minutes'.format(self.testing_duration))
        start = time.time()
        upload_log_time = start

        if self.testing_duration:
            testing_duration = int(self.testing_duration) * 60

            def _get_share(user, share_id):
                result = user.get_shares(share_id)
                if result:
                    self.count_passed += 1
                else:
                    self.count_failed += 1

            while (time.time() - start) < testing_duration:
                try:
                    for i in range(0, 5):
                        if self.env.cloud_env != 'prod':
                            self.log.info('*** Getting the share API from the created share by user1 (Get private share API testing) ***')
                            t = threading.Thread(name='GetPrivateShare%s' % i, target=_get_share, args=(user_list["rest_u{}".format(i+1)], share_id))
                            worker.append(t)

                        self.log.info('*** Getting the share API from the created share by user1 (Get public share API testing) ***')
                        w = threading.Thread(name='GetPublicShare%s' % i, target=_get_share, args=(user_list["rest_u{}".format(i+1)], share_id2))
                        worker.append(w)
                        if self.env.cloud_env != 'prod':
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
                        if not self.env.dry_run:
                            self._upload_result()
                        self._show_current_result()
                        upload_log_time = time.time()

            if self.count_passed != 0 or self.count_failed != 0:
                if not self.env.dry_run:
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
                'build': self.uut.get('firmware'),
                'shareAccessPassed': int(self.count_passed),
                'shareAccessFailed': int(self.count_failed),
                'product': self.uut.get('model'),
                }

        response = requests.post(url=self.env.logstash_server_url, data=json.dumps(data), headers=headers)
        if response.status_code == 200:
            self.log.info('Uploaded JSON results to logstash server {}'.format(self.env.logstash_server_url))
        else:
            error_message = 'Upload to logstash server {0} failed, {1}, error message: {2}'.\
                             format(self.env.logstash_server_url, response.status_code, response.content)
            raise self.err.StopTest(error_message)


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        Examples: ./run.sh integration_tests/concurrent_sharing_stress.py --uut_ip 10.0.0.13 --cloud_env qa1 --dry_run --debug_middleware\
        --testing_duration 2
        """)
    parser.add_argument('--testing_duration', help='Total testing duration (Minutes)', metavar='duration', default='60')

    test = ConcurrentSharingStress(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
