# -*- coding: utf-8 -*-
""" Test for pure API onboarding and reset.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import logging
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.restAPI import RestAPI


def timing(f):
    def wrapper(*args, **kwargs):
        self = args[0]
        start_time = time.time()
        try:
            return f(*args, **kwargs)
        finally:
            end_time = time.time()
            self.log.info('Onboading prcoess take {}s'.format(end_time - start_time))
    return wrapper


class OnboardingAndReset(TestCase):

    TEST_SUITE = 'RESTSDK Functional Tests'
    TEST_NAME = 'Onboarding and reset'
    # Popcorn
    TEST_TYPE = 'functional'
    TEST_JIRA_ID = ''
    PRIORITY = 'blocker'
    COMPONENT = 'REST SDK'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'adb': False,
        'uut_owner': False
    }

    def init(self):
        self.completed_step = 0

    def before_test(self):
        self.start_time = self.end_time = None
        self.rest_client = RestAPI(
            env=self.env.cloud_env, username=self.env.username, password=self.env.password, debug=True, 
            stream_log_level=logging.DEBUG, init_session=False)
        self.rest_client.update_service_urls()
        # reset status if previos factory reset is pass
        if self.completed_step == 3:
            self.completed_step = 0

    def test(self):
        if self.completed_step == 0:
            self.retry_to_onbaord()
            self.completed_step = 1

        if not self.rest_client.url_prefix:
            self.check_attached_device_and_update_url()

        if self.completed_step == 1:
            self.retry_api_call(f=self.rest_client.enable_pip) # TODO: update call?
            self.completed_step = 2

        if self.completed_step == 2:
            self.rest_client.factory_reset()
            self.completed_step = 3

            if self.sleep_interval:
                self.log.info('Sleep {} s...'.format(self.sleep_interval))
                time.sleep(self.sleep_interval)

    def retry_api_call(self, f, args=[], kwargs={}, status_code='429', try_times=12, delay=60*5):
        for idx in xrange(1, try_times+1):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                if status_code in str(e):
                    self.log.warning('Got error: {}'.format(e))
                    self.log.info('Wait for {} s and retry...'.format(delay))
                    time.sleep(delay)
                else:
                    raise
                    
    @timing
    def retry_to_onbaord(self):
        max_retry = 11
        for times in xrange(1, max_retry): 
            self.log.info('#{} to onboard'.format(times))
            if self.simulate_onboard(): break
            if times != max_retry-1:
                self.log.info('Wait for 5 mins and retry...')
                time.sleep(60*5)

    def simulate_onboard(self):
        onboarded, onboarded_device = self.search_device_and_onboard()
        if not onboarded: return False

        device_info = self.check_attached_device_and_update_url()

        if onboarded_device and device_info['deviceId'] != onboarded_device['deviceId']:
            raise self.err.TestFailure('Device ID is not correct')
        if device_info['attachedStatus'] != 'APPROVED':
            raise self.err.TestFailure('attachedStatus is not APPROVED')

        return True

    def check_attached_device_and_update_url(self):
        # check user's device
        resp = self.rest_client.get_devices_info_per_specific_user()
        if len(resp) != 1:
            self.log.info('Device list: {}'.format(resp))
            raise self.err.TestFailure('User has attached more than 1 device')

        # expect the only one device is using in test.
        device_info = resp[0]
        self.log.info('Device info from user: {}'.format(device_info))

        # update proxy URL to client
        self.rest_client.update_url_prefix(url_prefix=device_info.get('network', {}).get('proxyURL'))

        return device_info

    def search_device_and_onboard(self):
        # simulate search device twice.
        max_retry = 2
        for times in xrange(max_retry):
            try: # status code >= 500 will auto retry 3 times.
                return True, self.rest_client.attach_user_to_device_with_code(security_code=self.security_code)
            except Exception as e:
                if '409' in str(e):
                    self.log.error('Device is already attached')
                    return True, None
                self.log.error(e)
                if times != max_retry-1:
                    self.log.info('Wait for 5 secs and retry...')
                    time.sleep(5)
        return False, None


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Onboarding and reset test on Kamino Android ***
        """)

    parser.add_argument('-sc', '--security_code', help='Security code to onboard device', required=True)
    parser.add_argument('-si', '--sleep-interval', help='Sleep interval to wait reset complete', type=int, default=0)

    if OnboardingAndReset(parser).main():
        sys.exit(0)
    sys.exit(1)
